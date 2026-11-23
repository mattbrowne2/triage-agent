from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.runnables import RunnableLambda

from evals.judge import main as main_module
from evals.judge.models import CalibrationReport, HumanLabels, JudgeVerdict, LabelledReport, LabelSet, Verdict
from evals.models import TriageOutcome


class FakeRunsClient:
    def __init__(self, runs: list[SimpleNamespace], case_ids: dict[str, str]) -> None:
        self.runs = runs
        self.case_ids = case_ids

    def list_runs(self, *, project_name: str, is_root: bool) -> list[SimpleNamespace]:
        return [run for run in self.runs if run.experiment == project_name]

    def read_example(self, example_id: str) -> SimpleNamespace:
        return SimpleNamespace(
            metadata={"case_id": self.case_ids[example_id], "source": "human", "case_type": "correct"}
        )


def test_export_writes_one_unlabelled_report_per_case_in_run_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    outcome_factory: Callable[..., TriageOutcome],
) -> None:
    outputs = outcome_factory().model_dump(mode="json")
    runs = [
        SimpleNamespace(
            id=f"run-{index}",
            experiment="triage-rag-1a2b",
            reference_example_id="example-1",
            start_time=datetime(2026, 11, 22, 17, minute, tzinfo=UTC),
            inputs={"alert": "ALR-8812", "as_of": "2026-11-17T02:15:00Z"},
            outputs=outputs,
        )
        for index, minute in ((2, 5), (1, 1))
    ]
    monkeypatch.setattr(main_module, "Client", lambda: FakeRunsClient(runs, {"example-1": "human-correct"}))
    monkeypatch.setattr(main_module, "LABELS_PATH", tmp_path / "judge_labels.json")
    monkeypatch.setattr("sys.argv", ["calibrate-judge", "export", "--experiments", "triage-rag-1a2b"])

    main_module.main()

    label_set = LabelSet.model_validate_json((tmp_path / "judge_labels.json").read_text())
    assert [(report.run_id, report.case_id, report.alert, report.human) for report in label_set.reports] == [
        ("run-1", "human-correct", "ALR-8812", None)
    ]


def test_export_refuses_to_overwrite_a_labels_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    labels_path = tmp_path / "judge_labels.json"
    labels_path.write_text("my labels")
    monkeypatch.setattr(main_module, "Client", lambda: FakeRunsClient([], {}))
    monkeypatch.setattr(main_module, "LABELS_PATH", labels_path)
    monkeypatch.setattr("sys.argv", ["calibrate-judge", "export", "--experiments", "triage-rag-1a2b"])

    with pytest.raises(SystemExit, match="already exists"):
        main_module.main()

    assert labels_path.read_text() == "my labels"


def test_score_refuses_to_run_until_every_report_is_labelled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, labelled_report_factory: Callable[..., LabelledReport]
) -> None:
    labels_path = tmp_path / "judge_labels.json"
    labels_path.write_text(
        LabelSet(instructions="", reports=[labelled_report_factory("human-vague", None)]).model_dump_json()
    )
    monkeypatch.setattr(main_module, "LABELS_PATH", labels_path)
    monkeypatch.setattr("sys.argv", ["calibrate-judge", "score"])

    with pytest.raises(SystemExit, match="Unlabelled: human-vague"):
        main_module.main()


def test_score_judges_each_labelled_report_and_writes_the_calibration(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    labelled_report_factory: Callable[..., LabelledReport],
    human_labels_factory: Callable[..., HumanLabels],
    judge_verdict_factory: Callable[..., JudgeVerdict],
) -> None:
    labels_path = tmp_path / "judge_labels.json"
    human = human_labels_factory(trustworthy=Verdict.FAIL)
    labels_path.write_text(
        LabelSet(instructions="", reports=[labelled_report_factory("human-correct", human)]).model_dump_json()
    )
    judge_calls: list[Any] = []
    verdict = judge_verdict_factory()
    monkeypatch.setattr(
        main_module, "build_judge", lambda settings: RunnableLambda(lambda messages: judge_calls.append(1) or verdict)
    )
    monkeypatch.setattr(main_module, "LABELS_PATH", labels_path)
    monkeypatch.setattr(main_module, "RESULTS_PATH", tmp_path / "judge_calibration.json")
    monkeypatch.setattr("sys.argv", ["calibrate-judge", "score"])

    main_module.main()

    report = CalibrationReport.model_validate_json((tmp_path / "judge_calibration.json").read_text())
    assert (len(judge_calls), report.labelled, [item.criterion for item in report.disagreements]) == (
        1,
        1,
        ["trustworthy"],
    )
    first_line = capsys.readouterr().out.splitlines()[0]
    assert first_line == f"judge: {main_module._settings.JUDGE_MODEL} on 1 labelled reports"
