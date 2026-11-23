from collections.abc import Callable
from importlib.metadata import version

from fastapi.testclient import TestClient
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.tools import StructuredTool

from incident_triage.agent.triage_agent import build_triage_agent
from incident_triage.models.alert import Alert
from incident_triage.models.triage_report import TriageReport
from incident_triage.settings import LLMProvider
from triage_api.app import create_app
from triage_api.models import Triage, TriageStatus


def test_health_reports_ok(triage_client_factory: Callable[..., TestClient]) -> None:
    response = triage_client_factory().get("/health")

    assert (response.status_code, response.json()) == (200, {"status": "ok"})


def test_version_reports_installed_package_version(triage_client_factory: Callable[..., TestClient]) -> None:
    response = triage_client_factory().get("/version")

    assert (response.status_code, response.json()) == (200, {"version": version("incident-triage")})


def test_post_alert_accepts_it_as_queued_and_triage_completes_in_background(
    triage_client_factory: Callable[..., TestClient],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    checkout_error_rate_alert: Alert,
    confirmed_triage_report: TriageReport,
) -> None:
    client = triage_client_factory(report_submission_factory(confirmed_triage_report))

    accepted = client.post("/alerts", json=checkout_error_rate_alert.model_dump(mode="json"))
    completed = client.get(f"/triages/{checkout_error_rate_alert.id}")

    assert [(accepted.status_code, accepted.json()), (completed.status_code, completed.json())] == [
        (202, Triage(alert=checkout_error_rate_alert).model_dump(mode="json")),
        (
            200,
            Triage(
                alert=checkout_error_rate_alert, status=TriageStatus.COMPLETED, report=confirmed_triage_report
            ).model_dump(mode="json"),
        ),
    ]


def test_post_repeated_alert_returns_existing_triage_without_running_again(
    triage_client_factory: Callable[..., TestClient],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    checkout_error_rate_alert: Alert,
    confirmed_triage_report: TriageReport,
) -> None:
    client = triage_client_factory(report_submission_factory(confirmed_triage_report))
    client.post("/alerts", json=checkout_error_rate_alert.model_dump(mode="json"))

    repeated = client.post("/alerts", json=checkout_error_rate_alert.model_dump(mode="json"))
    after_repeat = client.get(f"/triages/{checkout_error_rate_alert.id}")
    completed = Triage(
        alert=checkout_error_rate_alert, status=TriageStatus.COMPLETED, report=confirmed_triage_report
    ).model_dump(mode="json")

    assert [(repeated.status_code, repeated.json()), after_repeat.json()] == [(200, completed), completed]


def test_post_alert_rejects_invalid_payload(
    triage_client_factory: Callable[..., TestClient], checkout_error_rate_alert: Alert
) -> None:
    invalid_alert = checkout_error_rate_alert.model_dump(mode="json") | {"log_count": 0}

    response = triage_client_factory().post("/alerts", json=invalid_alert)

    assert response.status_code == 422


def test_get_unknown_triage_is_not_found(triage_client_factory: Callable[..., TestClient]) -> None:
    response = triage_client_factory().get("/triages/ALR-404")

    assert (response.status_code, response.json()) == (404, {"detail": "No triage for alert 'ALR-404'"})


def test_list_triages_returns_every_received_alert(
    triage_client_factory: Callable[..., TestClient],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    checkout_error_rate_alert: Alert,
    confirmed_triage_report: TriageReport,
) -> None:
    client = triage_client_factory(report_submission_factory(confirmed_triage_report))
    client.post("/alerts", json=checkout_error_rate_alert.model_dump(mode="json"))

    response = client.get("/triages")

    assert (response.status_code, response.json()) == (
        200,
        [
            Triage(
                alert=checkout_error_rate_alert, status=TriageStatus.COMPLETED, report=confirmed_triage_report
            ).model_dump(mode="json")
        ],
    )


def test_post_alert_builds_the_agent_for_that_alerts_ticket_key(
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    query_logs_tool: StructuredTool,
    checkout_error_rate_alert: Alert,
    confirmed_triage_report: TriageReport,
) -> None:
    model = scripted_chat_model_factory(report_submission_factory(confirmed_triage_report))
    agent = build_triage_agent(model, [query_logs_tool], LLMProvider.ANTHROPIC)
    alert_keys: list[str] = []
    client = TestClient(create_app(lambda alert_key: alert_keys.append(alert_key) or agent, max_steps=10))

    client.post("/alerts", json=checkout_error_rate_alert.model_dump(mode="json"))

    assert alert_keys == [checkout_error_rate_alert.id]
