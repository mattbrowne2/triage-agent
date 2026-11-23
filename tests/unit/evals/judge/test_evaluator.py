from collections.abc import Callable
from typing import Any

from langchain_core.runnables import RunnableLambda
from langsmith.evaluation import EvaluationResult

from evals.judge.evaluator import build_judge_evaluator
from evals.judge.models import CriterionVerdict, JudgeVerdict, Verdict
from evals.models import TriageOutcome


INPUTS = {"alert": "ALR-8812: checkout-service 5xx since 02:09", "as_of": "2026-11-17T02:15:00Z"}


def test_judge_evaluator_scores_each_criterion_with_the_judges_reasoning(
    outcome_factory: Callable[..., TriageOutcome],
) -> None:
    verdict = JudgeVerdict(
        evidence_grounded=CriterionVerdict(reasoning="Every timestamp appears in a log result.", verdict=Verdict.PASS),
        confidence_calibrated=CriterionVerdict(
            reasoning="High confidence, but the report says the trigger was not found.", verdict=Verdict.FAIL
        ),
        next_steps_actionable=CriterionVerdict(reasoning="Names the rollback target.", verdict=Verdict.PASS),
        trustworthy=CriterionVerdict(reasoning="Would act on it after checking the deploy.", verdict=Verdict.FAIL),
    )
    received: list[Any] = []
    judge = RunnableLambda(lambda messages: received.append(messages) or verdict)

    results = build_judge_evaluator(judge)(INPUTS, outcome_factory().model_dump(mode="json"))

    assert (results, len(received)) == (
        {
            "results": [
                EvaluationResult(
                    key="judge_evidence_grounded", score=1, comment="Every timestamp appears in a log result."
                ),
                EvaluationResult(
                    key="judge_confidence_calibrated",
                    score=0,
                    comment="High confidence, but the report says the trigger was not found.",
                ),
                EvaluationResult(key="judge_next_steps_actionable", score=1, comment="Names the rollback target."),
                EvaluationResult(
                    key="judge_trustworthy", score=0, comment="Would act on it after checking the deploy."
                ),
            ]
        },
        1,
    )


def test_judge_evaluator_does_not_call_the_judge_when_there_is_no_report(failed_outcome: TriageOutcome) -> None:
    def unexpected_call(messages: Any) -> JudgeVerdict:
        raise AssertionError("judge should not be called")

    results = build_judge_evaluator(RunnableLambda(unexpected_call))(INPUTS, failed_outcome.model_dump(mode="json"))

    assert [(result.key, result.score, result.comment) for result in results["results"]] == [
        ("judge_evidence_grounded", None, "no report"),
        ("judge_confidence_calibrated", None, "no report"),
        ("judge_next_steps_actionable", None, "no report"),
        ("judge_trustworthy", None, "no report"),
    ]


def test_judge_evaluator_records_a_judge_error_instead_of_failing_the_experiment(
    outcome_factory: Callable[..., TriageOutcome],
) -> None:
    def unavailable(messages: Any) -> JudgeVerdict:
        raise ConnectionError("judge provider unreachable")

    results = build_judge_evaluator(RunnableLambda(unavailable))(INPUTS, outcome_factory().model_dump(mode="json"))

    assert {(result.score, result.comment) for result in results["results"]} == {
        (None, "judge failed: ConnectionError: judge provider unreachable")
    }
