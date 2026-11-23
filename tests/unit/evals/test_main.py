from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableLambda

from evals import main as main_module
from evals.models import ExperimentSummary


def test_main_runs_the_requested_arm_and_writes_its_summary(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    langsmith_client_factory: Callable[..., Any],
    experiment_results_factory: Callable[[str], Any],
    scripted_chat_model_factory: Callable[..., BaseChatModel],
) -> None:
    evaluate_options: list[dict[str, Any]] = []

    def fake_evaluate(target: Callable[..., Any], **options: Any) -> Any:
        evaluate_options.append(options)
        return experiment_results_factory("triage-baseline-1a2b")

    monkeypatch.setattr(main_module, "Client", lambda: langsmith_client_factory(existing=set()))
    monkeypatch.setattr(main_module, "evaluate", fake_evaluate)
    monkeypatch.setattr(main_module, "build_chat_model", lambda settings: scripted_chat_model_factory())
    monkeypatch.setattr(main_module, "build_judge", lambda settings: RunnableLambda(lambda messages: None))
    monkeypatch.setattr(main_module, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr("sys.argv", ["run-evals", "--arm", "baseline", "--repetitions", "2"])

    main_module.main()

    assert (
        [
            (
                options["experiment_prefix"],
                options["num_repetitions"],
                options["metadata"]["arm"],
                options["metadata"]["judge_model"],
                [evaluator.__name__ for evaluator in options["evaluators"]][-1],
            )
            for options in evaluate_options
        ],
        ExperimentSummary.model_validate_json((tmp_path / "triage-baseline-1a2b.json").read_text()),
        capsys.readouterr().out.splitlines()[0],
    ) == (
        [("triage-baseline", 2, "baseline", "claude-opus-5-5", "llm_judge")],
        ExperimentSummary(experiment="triage-baseline-1a2b", arm="baseline", overall=[], slices=[]),
        "experiment: triage-baseline-1a2b (arm: baseline)",
    )


def test_main_can_skip_the_judge_for_cheap_runs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    langsmith_client_factory: Callable[..., Any],
    experiment_results_factory: Callable[[str], Any],
    scripted_chat_model_factory: Callable[..., BaseChatModel],
) -> None:
    evaluate_options: list[dict[str, Any]] = []

    def fake_evaluate(target: Callable[..., Any], **options: Any) -> Any:
        evaluate_options.append(options)
        return experiment_results_factory("triage-baseline-3c4d")

    monkeypatch.setattr(main_module, "Client", lambda: langsmith_client_factory(existing=set()))
    monkeypatch.setattr(main_module, "evaluate", fake_evaluate)
    monkeypatch.setattr(main_module, "build_chat_model", lambda settings: scripted_chat_model_factory())
    monkeypatch.setattr(main_module, "RESULTS_DIR", tmp_path)
    monkeypatch.setattr("sys.argv", ["run-evals", "--arm", "baseline", "--skip-judge"])

    main_module.main()

    assert [
        (options["metadata"]["judge_model"], "llm_judge" in [evaluator.__name__ for evaluator in options["evaluators"]])
        for options in evaluate_options
    ] == [(None, False)]
