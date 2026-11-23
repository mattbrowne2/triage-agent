from argparse import ArgumentParser
from enum import StrEnum, auto
from pathlib import Path

from langchain_core.tools import BaseTool
from langsmith import Client, evaluate

from evals.dataset import dataset_name, ensure_dataset
from evals.evaluators import Evaluator, build_evaluators
from evals.judge.evaluator import JudgeEvaluator, build_judge_evaluator
from evals.judge.model import build_judge
from evals.models import EvalSuite, ExperimentMetadata
from evals.summary import format_summary, scored_example, summarize
from evals.target import build_triage_target
from incident_triage.agent.chat_model import build_chat_model
from incident_triage.incident_store.embeddings import build_embeddings
from incident_triage.incident_store.index import IncidentIndex
from incident_triage.models.datadog import LogArchive
from incident_triage.models.incident import IncidentArchive
from incident_triage.settings import Settings, get_settings
from incident_triage.tools.search_past_incidents import build_search_past_incidents_tool


_settings = get_settings()

CASES_PATH = Path("data/evals/triage_cases.json")
RESULTS_DIR = Path("eval_results")


class Arm(StrEnum):
    BASELINE = auto()
    RAG = auto()


def incident_tools(arm: Arm, settings: Settings) -> list[BaseTool]:
    match arm:
        case Arm.BASELINE:
            return []
        case Arm.RAG:
            index = IncidentIndex.from_file(
                settings.INCIDENTS_PATH, build_embeddings(settings), settings.INCIDENT_MIN_SIMILARITY
            )
            return [build_search_past_incidents_tool(index)]


def judge_evaluators(skip_judge: bool, settings: Settings) -> list[JudgeEvaluator]:
    match skip_judge:
        case True:
            return []
        case False:
            return [build_judge_evaluator(build_judge(settings))]


def main() -> None:
    parser = ArgumentParser(description="Run the triage eval suite through LangSmith")
    parser.add_argument("--arm", type=Arm, choices=list(Arm), required=True)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--skip-judge", action="store_true", help="Run only the deterministic checks")
    arguments = parser.parse_args()

    suite_json = CASES_PATH.read_text()
    name = dataset_name(suite_json)
    client = Client()
    ensure_dataset(client, EvalSuite.model_validate_json(suite_json), name)

    archive = LogArchive.model_validate_json(_settings.DATADOG_LOGS_PATH.read_text())
    known_incidents = IncidentArchive.model_validate_json(_settings.INCIDENTS_PATH.read_text()).incidents
    target = build_triage_target(
        build_chat_model(_settings),
        archive,
        incident_tools(arguments.arm, _settings),
        _settings.LLM_PROVIDER,
        _settings.MAX_AGENT_STEPS,
    )
    metadata = ExperimentMetadata(
        arm=arguments.arm,
        dataset=name,
        provider=_settings.LLM_PROVIDER,
        model=_settings.LLM_MODEL,
        reasoning_effort=_settings.LLM_REASONING_EFFORT,
        judge_model=None if arguments.skip_judge else _settings.JUDGE_MODEL,
    )
    evaluators: list[Evaluator | JudgeEvaluator] = [
        *build_evaluators(frozenset(incident.key for incident in known_incidents)),
        *judge_evaluators(arguments.skip_judge, _settings),
    ]

    results = evaluate(
        target,
        data=name,
        evaluators=evaluators,
        experiment_prefix=f"triage-{arguments.arm}",
        metadata=metadata.model_dump(),
        max_concurrency=arguments.concurrency,
        num_repetitions=arguments.repetitions,
        client=client,
    )

    summary = summarize(results.experiment_name, arguments.arm, [scored_example(row) for row in results])
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / f"{summary.experiment}.json").write_text(summary.model_dump_json(indent=2))
    print(format_summary(summary))


if __name__ == "__main__":
    main()
