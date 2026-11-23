from collections.abc import Callable

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from langsmith.evaluation import EvaluationResult, EvaluationResults
from pydantic import BaseModel, JsonValue

from evals.judge.models import Criterion, JudgeVerdict, Verdict
from evals.judge.prompt import judge_messages
from evals.models import CaseInput, TriageOutcome


type Judge = Runnable[LanguageModelInput, dict | BaseModel]
type JudgeEvaluator = Callable[[dict[str, JsonValue], dict[str, JsonValue]], EvaluationResults]


def build_judge_evaluator(judge: Judge) -> JudgeEvaluator:
    def llm_judge(inputs: dict[str, JsonValue], outputs: dict[str, JsonValue]) -> EvaluationResults:
        case = CaseInput.model_validate(inputs)
        outcome = TriageOutcome.model_validate(outputs)
        match outcome.report:
            case None:
                return _unscored("no report")
            case report:
                return _judge(judge, judge_messages(case.alert, outcome.tool_calls, report))

    return llm_judge


def _judge(judge: Judge, messages: list[BaseMessage]) -> EvaluationResults:
    try:
        verdict = JudgeVerdict.model_validate(judge.invoke(messages))
    except Exception as error:
        return _unscored(f"judge failed: {type(error).__name__}: {error}")
    return EvaluationResults(
        results=[
            EvaluationResult(
                key=f"judge_{criterion}",
                score=int(getattr(verdict, criterion).verdict == Verdict.PASS),
                comment=getattr(verdict, criterion).reasoning,
            )
            for criterion in Criterion
        ]
    )


def _unscored(reason: str) -> EvaluationResults:
    return EvaluationResults(
        results=[EvaluationResult(key=f"judge_{criterion}", score=None, comment=reason) for criterion in Criterion]
    )
