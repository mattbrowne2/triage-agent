import pytest

from incident_triage.models.alert import Alert
from incident_triage.models.triage_report import TriageReport
from triage_api.errors import TriageNotFoundError
from triage_api.models import Triage, TriageStatus
from triage_api.store import TriageStore


def test_add_queues_a_new_triage_for_the_alert(triage_store: TriageStore, checkout_error_rate_alert: Alert) -> None:
    result = triage_store.add(checkout_error_rate_alert)

    assert (result, triage_store.get(checkout_error_rate_alert.id)) == (
        (Triage(alert=checkout_error_rate_alert, status=TriageStatus.QUEUED), True),
        Triage(alert=checkout_error_rate_alert, status=TriageStatus.QUEUED),
    )


def test_add_returns_existing_triage_when_alert_was_already_received(
    store_with_checkout_alert: TriageStore,
    checkout_error_rate_alert: Alert,
    confirmed_triage_report: TriageReport,
) -> None:
    completed = Triage(alert=checkout_error_rate_alert, status=TriageStatus.COMPLETED, report=confirmed_triage_report)
    store_with_checkout_alert.save(completed)

    assert store_with_checkout_alert.add(checkout_error_rate_alert) == (completed, False)


def test_get_raises_for_unknown_alert(triage_store: TriageStore) -> None:
    with pytest.raises(TriageNotFoundError, match="No triage for alert 'ALR-404'"):
        triage_store.get("ALR-404")


def test_list_returns_triages_in_the_order_alerts_arrived(
    store_with_checkout_alert: TriageStore, checkout_error_rate_alert: Alert
) -> None:
    payment_alert = checkout_error_rate_alert.model_copy(update={"id": "payment-alert", "service": "payment-service"})
    store_with_checkout_alert.add(payment_alert)

    assert store_with_checkout_alert.list() == [
        Triage(alert=checkout_error_rate_alert, status=TriageStatus.QUEUED),
        Triage(alert=payment_alert, status=TriageStatus.QUEUED),
    ]
