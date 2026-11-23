import pytest
from pydantic import ValidationError

from incident_triage.models.triage_report import Confidence, RelatedIncident, TriageReport


def test_report_parses_tool_call_arguments_for_an_alert_the_logs_contradict() -> None:
    arguments = {
        "alert_confirmed": False,
        "alert_discrepancy": "Alert names inventory-service, but the failing service is checkout-service",
        "root_cause": "payment-service v2.14.0 rejects currency_code",
        "confidence": "medium",
        "evidence": ["315 checkout-service errors since 02:09"],
        "impact": "Checkout failing since 02:09 UTC",
        "next_steps": ["Roll back payment-service"],
        "ruled_out": ["inventory-service timeouts"],
        "related_incidents": [],
        "ticket_key": None,
    }

    report = TriageReport.model_validate(arguments)

    assert report == TriageReport(
        alert_confirmed=False,
        alert_discrepancy="Alert names inventory-service, but the failing service is checkout-service",
        root_cause="payment-service v2.14.0 rejects currency_code",
        confidence=Confidence.MEDIUM,
        evidence=["315 checkout-service errors since 02:09"],
        impact="Checkout failing since 02:09 UTC",
        next_steps=["Roll back payment-service"],
        ruled_out=["inventory-service timeouts"],
        related_incidents=[],
        ticket_key=None,
    )


def test_alert_confirmed_is_false_only_for_contradicted_claims_not_uncheckable_or_unstated_ones() -> None:
    description = TriageReport.model_json_schema()["properties"]["alert_confirmed"]["description"]

    assert description == (
        "True if the logs show the incident the alert describes and contradict none of its claims: the affected "
        "service, the symptom, and a start time if the alert states one. A claim the logs cannot check, such as a "
        "rate that needs request counts, is not a contradiction, and neither is a detail the alert doesn't state. "
        "False only if the logs contradict a claim or show no incident."
    )


def test_report_requires_alert_confirmed_to_be_stated(confirmed_triage_report: TriageReport) -> None:
    arguments = confirmed_triage_report.model_dump(mode="json", exclude={"alert_confirmed"})

    with pytest.raises(ValidationError, match="alert_confirmed"):
        TriageReport.model_validate(arguments)


def test_report_allows_no_root_cause_when_evidence_does_not_support_one() -> None:
    report = TriageReport(
        alert_confirmed=False,
        alert_discrepancy="No elevated errors in the alert window",
        root_cause=None,
        confidence=Confidence.LOW,
        evidence=["0 error logs between 02:00 and 02:30"],
        impact="None observed",
        next_steps=["Check the monitor's threshold"],
        ruled_out=["inventory-service timeouts, present all along"],
        related_incidents=[],
        ticket_key=None,
    )

    assert report.root_cause is None


def test_report_carries_related_past_incidents_with_their_fix_links(confirmed_triage_report: TriageReport) -> None:
    arguments = confirmed_triage_report.model_dump(mode="json")

    assert TriageReport.model_validate(arguments).related_incidents == [
        RelatedIncident(
            key="INC-311",
            why_similar="A payment-service deploy changed the charge request schema and checkout's calls got 400s",
            what_differs="This time the field is currency_code and the version is v2.14.0",
            change_urls=["https://git.example.com/payments/pull/1432"],
        )
    ]


def test_report_requires_related_incidents_to_be_stated_even_when_empty(
    confirmed_triage_report: TriageReport,
) -> None:
    arguments = confirmed_triage_report.model_dump(mode="json", exclude={"related_incidents"})

    with pytest.raises(ValidationError, match="related_incidents"):
        TriageReport.model_validate(arguments)


def test_report_requires_ticket_key_to_be_stated_even_when_no_ticket_was_filed(
    confirmed_triage_report: TriageReport,
) -> None:
    arguments = confirmed_triage_report.model_dump(mode="json", exclude={"ticket_key"})

    with pytest.raises(ValidationError, match="ticket_key"):
        TriageReport.model_validate(arguments)
