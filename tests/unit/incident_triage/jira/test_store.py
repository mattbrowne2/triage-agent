from datetime import datetime
from pathlib import Path

import pytest

from incident_triage.jira.errors import TicketContainsPersonalDataError
from incident_triage.jira.store import FileJiraStore, JiraStore
from incident_triage.models.jira import JiraIssue, JiraPriority, TicketRequest


def test_create_files_a_numbered_ticket_for_the_alert(
    jira_store: JiraStore, rollback_ticket_request: TicketRequest, jira_now: datetime
) -> None:
    issue, created = jira_store.create("error-rate:checkout-service:2026-11-17T02:05:00Z", rollback_ticket_request)

    assert (issue, created, jira_store.issues()) == (
        JiraIssue(
            id="10001",
            key="OPS-1",
            summary=rollback_ticket_request.summary,
            description=rollback_ticket_request.description,
            priority=JiraPriority.HIGHEST,
            service="payment-service",
            alert_key="error-rate:checkout-service:2026-11-17T02:05:00Z",
            created_at=jira_now,
        ),
        True,
        [issue],
    )


def test_create_returns_the_existing_ticket_when_the_alert_already_has_one(
    jira_store: JiraStore, rollback_ticket_request: TicketRequest
) -> None:
    first, _ = jira_store.create("alert-1", rollback_ticket_request)

    second, created = jira_store.create("alert-1", rollback_ticket_request.model_copy(update={"summary": "Again"}))

    assert (second, created, len(jira_store.issues())) == (first, False, 1)


def test_create_numbers_tickets_for_different_alerts_in_order(
    jira_store: JiraStore, rollback_ticket_request: TicketRequest
) -> None:
    jira_store.create("alert-1", rollback_ticket_request)
    second, _ = jira_store.create("alert-2", rollback_ticket_request)

    assert (second.id, second.key) == ("10002", "OPS-2")


def test_create_rejects_a_ticket_containing_customer_emails(
    jira_store: JiraStore, rollback_ticket_request: TicketRequest
) -> None:
    leaking = rollback_ticket_request.model_copy(
        update={"description": "Failing for customer=priya.nguyen@example.com and sam.smith@example.com"}
    )

    with pytest.raises(TicketContainsPersonalDataError, match="2 customer email addresses"):
        jira_store.create("alert-1", leaking)

    assert jira_store.issues() == []


def test_file_store_persists_tickets_and_reloads_them(
    tmp_path: Path, rollback_ticket_request: TicketRequest, jira_now: datetime
) -> None:
    path = tmp_path / "tickets.json"
    issue, _ = FileJiraStore(path, clock=lambda: jira_now).create("alert-1", rollback_ticket_request)

    reloaded = FileJiraStore(path, clock=lambda: jira_now)

    assert (reloaded.issues(), reloaded.create("alert-1", rollback_ticket_request)) == ([issue], (issue, False))
