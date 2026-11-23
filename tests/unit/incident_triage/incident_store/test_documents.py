from incident_triage.incident_store.documents import incident_document
from incident_triage.models.incident import PastIncident


def test_document_for_resolved_incident_holds_title_service_symptoms_and_confirmed_cause(
    resolved_contract_incident: PastIncident,
) -> None:
    assert incident_document(resolved_contract_incident) == (
        "Checkout failing after payment-service deploy made a request field required\n"
        "Service: checkout-service\n"
        "Symptoms: checkout-service returned HTTP 500. PaymentClientError: 400 Bad Request - missing field "
        "'amount_minor'.\n"
        "Confirmed root cause: payment-service v2.11.0 made 'amount_minor' required"
    )


def test_document_for_open_incident_has_no_root_cause(open_load_balancer_incident: PastIncident) -> None:
    assert incident_document(open_load_balancer_incident) == (
        "Intermittent 502s from the load balancer in front of web-frontend\n"
        "Service: web-frontend\n"
        "Symptoms: web-frontend returned occasional HTTP 502 Bad Gateway responses. Not yet explained."
    )
