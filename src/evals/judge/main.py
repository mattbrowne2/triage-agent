from argparse import ArgumentParser
from pathlib import Path

from langsmith import Client
from langsmith.schemas import Run

from evals.judge.calibration import calibration_report, format_calibration, select_for_labelling
from evals.judge.evaluator import Judge
from evals.judge.model import build_judge
from evals.judge.models import JudgedReport, JudgeVerdict, LabelledReport, LabelSet
from evals.judge.prompt import judge_messages
from evals.models import CaseInput, CaseMetadata, TriageOutcome
from incident_triage.settings import get_settings


_settings = get_settings()

LABELS_PATH = Path("data/evals/judge_labels.json")
RESULTS_PATH = Path("eval_results/judge_calibration.json")
INSTRUCTIONS = (
    "Label each report yourself before looking at any judge output. Replace `human: null` with "
    '{"evidence_grounded": "pass" or "fail", "confidence_calibrated": ..., "next_steps_actionable": ..., '
    '"trustworthy": ..., "notes": "why, especially for any fail"}. '
    "Use the rubric in src/evals/judge/prompts/judge.md. Then run `make calibrate-judge`."
)


def main() -> None:
    parser = ArgumentParser(description="Calibrate the LLM judge against human labels")
    commands = parser.add_subparsers(dest="command", required=True)
    export_parser = commands.add_parser("export", help="Write one report per case from each experiment for labelling")
    export_parser.add_argument("--experiments", nargs="+", required=True)
    commands.add_parser("score", help="Run the judge on the labelled reports and measure agreement")
    arguments = parser.parse_args()

    match arguments.command:
        case "export":
            export(arguments.experiments)
        case "score":
            score()


def export(experiments: list[str]) -> None:
    client = Client()
    reports = [
        _labelled_report(client, experiment, run)
        for experiment in experiments
        for run in sorted(client.list_runs(project_name=experiment, is_root=True), key=lambda run: run.start_time)
    ]
    label_set = LabelSet(instructions=INSTRUCTIONS, reports=select_for_labelling(reports))
    try:
        with LABELS_PATH.open("x") as labels_file:
            labels_file.write(label_set.model_dump_json(indent=2))
    except FileExistsError as error:
        raise SystemExit(f"{LABELS_PATH} already exists and may hold your labels. Move it aside first.") from error
    print(f"Wrote {len(label_set.reports)} reports to {LABELS_PATH}. {INSTRUCTIONS}")


def score() -> None:
    label_set = LabelSet.model_validate_json(LABELS_PATH.read_text())
    unlabelled = [report.case_id for report in label_set.reports if report.human is None]
    if unlabelled:
        raise SystemExit(f"Label every report in {LABELS_PATH} first. Unlabelled: {', '.join(unlabelled)}")
    judge = build_judge(_settings)
    judged = [
        JudgedReport(report=report, human=human, judge=_judge(judge, report))
        for report in label_set.reports
        if (human := report.human) is not None
    ]
    report = calibration_report(_settings.JUDGE_MODEL, judged)
    RESULTS_PATH.parent.mkdir(exist_ok=True)
    RESULTS_PATH.write_text(report.model_dump_json(indent=2))
    print(format_calibration(report))


def _labelled_report(client: Client, experiment: str, run: Run) -> LabelledReport:
    match run.reference_example_id:
        case None:
            raise SystemExit(f"Run {run.id} in {experiment} is not linked to a dataset example")
        case example_id:
            example = client.read_example(example_id)
    return LabelledReport(
        run_id=str(run.id),
        experiment=experiment,
        case_id=CaseMetadata.model_validate(example.metadata).case_id,
        alert=CaseInput.model_validate(run.inputs).alert,
        outcome=TriageOutcome.model_validate(run.outputs),
        human=None,
    )


def _judge(judge: Judge, report: LabelledReport) -> JudgeVerdict:
    match report.outcome.report:
        case None:
            raise SystemExit(f"{report.case_id} has no report to judge")
        case triage_report:
            messages = judge_messages(report.alert, report.outcome.tool_calls, triage_report)
    try:
        return JudgeVerdict.model_validate(judge.invoke(messages))
    except Exception as error:
        raise SystemExit(f"Judge failed on {report.case_id} ({report.run_id}): {error}") from error


if __name__ == "__main__":
    main()
