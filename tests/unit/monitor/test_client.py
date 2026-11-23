from collections.abc import Callable

import httpx
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from incident_triage.models.alert import Alert
from incident_triage.models.triage_report import TriageReport
from monitor.client import build_client, send_alert
from monitor.models import Delivery


def test_alert_sent_by_monitor_is_accepted_by_the_triage_api(
    triage_client_factory: Callable[..., TestClient],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    checkout_error_rate_alert: Alert,
    confirmed_triage_report: TriageReport,
) -> None:
    client = triage_client_factory(report_submission_factory(confirmed_triage_report))

    assert send_alert(client, checkout_error_rate_alert) == Delivery(
        alert_id=checkout_error_rate_alert.id, delivered=True, detail="HTTP 202"
    )


def test_delivery_is_reported_as_failed_when_the_api_returns_a_server_error(checkout_error_rate_alert: Alert) -> None:
    client = httpx.Client(
        base_url="http://triage-api", transport=httpx.MockTransport(lambda request: httpx.Response(503))
    )

    assert send_alert(client, checkout_error_rate_alert) == Delivery(
        alert_id=checkout_error_rate_alert.id, delivered=False, detail="HTTP 503"
    )


def test_delivery_is_reported_as_failed_when_the_api_is_unreachable(checkout_error_rate_alert: Alert) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = httpx.Client(base_url="http://triage-api", transport=httpx.MockTransport(refuse))

    assert send_alert(client, checkout_error_rate_alert) == Delivery(
        alert_id=checkout_error_rate_alert.id, delivered=False, detail="ConnectError: connection refused"
    )


def test_build_client_targets_the_given_api_url() -> None:
    assert build_client("http://localhost:8000").base_url == httpx.URL("http://localhost:8000")
