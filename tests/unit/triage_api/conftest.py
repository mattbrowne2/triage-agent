import pytest

from incident_triage.models.alert import Alert
from triage_api.store import TriageStore


@pytest.fixture
def triage_store() -> TriageStore:
    return TriageStore()


@pytest.fixture
def store_with_checkout_alert(triage_store: TriageStore, checkout_error_rate_alert: Alert) -> TriageStore:
    triage_store.add(checkout_error_rate_alert)
    return triage_store
