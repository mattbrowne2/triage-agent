from collections.abc import Callable
from pathlib import Path

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from incident_triage import main as main_module
from incident_triage import wiring
from incident_triage.models.datadog import LogArchive
from incident_triage.models.triage_report import TriageReport
from incident_triage.settings import LLMProvider


def test_main_prints_the_triage_report_for_alert_given_on_command_line(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    log_archive: LogArchive,
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    confirmed_triage_report: TriageReport,
) -> None:
    logs_path = tmp_path / "logs.json"
    logs_path.write_text(log_archive.model_dump_json())
    monkeypatch.setattr(main_module._settings, "DATADOG_LOGS_PATH", logs_path)
    monkeypatch.setattr(main_module._settings, "LLM_PROVIDER", LLMProvider.ANTHROPIC)
    monkeypatch.setattr(main_module._settings, "JIRA_TICKETS_PATH", tmp_path / "tickets.json")
    monkeypatch.setattr(
        wiring,
        "build_chat_model",
        lambda settings: scripted_chat_model_factory(report_submission_factory(confirmed_triage_report)),
    )
    monkeypatch.setattr("sys.argv", ["incident-triage", "ALR-8812 checkout-service 5xx"])

    main_module.main()

    assert capsys.readouterr().out.rstrip().endswith(confirmed_triage_report.model_dump_json(indent=2))
