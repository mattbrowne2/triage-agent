from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from incident_triage.models.datadog import Log, LogArchive
from incident_triage.models.triage_report import TriageReport
from monitor import main as main_module
from monitor.models import Delivery


def test_main_replays_archive_and_prints_each_alert_delivery(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    checkout_burst_factory: Callable[[int, int], list[Log]],
    triage_client_factory: Callable[..., TestClient],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    confirmed_triage_report: TriageReport,
) -> None:
    logs_path = tmp_path / "logs.json"
    logs_path.write_text(LogArchive(data=checkout_burst_factory(2, 10)).model_dump_json())
    api_client = triage_client_factory(report_submission_factory(confirmed_triage_report))
    monkeypatch.setattr(main_module, "build_client", lambda api_url: api_client)
    monkeypatch.setattr("sys.argv", ["error-monitor", "--logs", str(logs_path), "--seconds-per-check", "0"])

    main_module.main()

    assert capsys.readouterr().out.splitlines() == [
        Delivery(
            alert_id="error-rate:checkout-service:2026-11-17T01:58:00Z", delivered=True, detail="HTTP 202"
        ).model_dump_json()
    ]
