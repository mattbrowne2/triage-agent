from collections.abc import Callable

from langsmith.evaluation import EvaluationResult

from evals.evaluators import (
    alert_confirmed_correct,
    build_citations_exist,
    expected_precedent_cited,
    forbidden_precedent_not_cited,
    no_customer_emails,
    report_produced,
    root_cause_correct,
    ruled_out_expected,
    searched_past_incidents,
    ticket_decision_correct,
    ticket_key_reported,
    tool_call_count,
)
from evals.models import ExpectedTriage, RootCauseExpectation, ToolCallRecord, TriageOutcome
from incident_triage.models.jira import JiraIssue
from incident_triage.models.triage_report import RelatedIncident


KNOWN_INCIDENTS = frozenset({"INC-311", "INC-298", "INC-287"})


def test_report_produced_passes_with_a_report_and_fails_with_the_runner_failure(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    failed_outcome: TriageOutcome,
    incident_expectation: ExpectedTriage,
) -> None:
    assert [
        report_produced(*as_dicts(outcome_factory(), incident_expectation)),
        report_produced(*as_dicts(failed_outcome, incident_expectation)),
    ] == [
        EvaluationResult(key="report_produced", score=1),
        EvaluationResult(
            key="report_produced", score=0, comment="Triage stopped after 25 steps without reaching a conclusion."
        ),
    ]


def test_alert_confirmed_correct_compares_with_expected_verdict(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
) -> None:
    contradicted = outcome_factory({"alert_confirmed": False})

    assert [
        alert_confirmed_correct(*as_dicts(outcome_factory(), incident_expectation)),
        alert_confirmed_correct(*as_dicts(contradicted, incident_expectation)),
    ] == [
        EvaluationResult(key="alert_confirmed_correct", score=1, comment="expected True, got True"),
        EvaluationResult(key="alert_confirmed_correct", score=0, comment="expected True, got False"),
    ]


def test_checks_that_need_a_report_fail_when_there_is_none(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    failed_outcome: TriageOutcome,
    incident_expectation: ExpectedTriage,
) -> None:
    arguments = as_dicts(failed_outcome, incident_expectation)

    assert [
        check(*arguments).score
        for check in (alert_confirmed_correct, root_cause_correct, ruled_out_expected, expected_precedent_cited)
    ] == [0, 0, 0, 0]


def test_root_cause_correct_needs_every_expected_term_case_insensitively(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
) -> None:
    named = outcome_factory({"root_cause": "Payment-service v2.14.0 rejects currency_code"})
    unversioned = outcome_factory({"root_cause": "payment-service rejects currency_code"})

    assert [
        root_cause_correct(*as_dicts(named, incident_expectation)).score,
        root_cause_correct(*as_dicts(unversioned, incident_expectation)).score,
    ] == [1, 0]


def test_root_cause_correct_expects_no_root_cause_for_a_false_alarm(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
) -> None:
    false_alarm = incident_expectation.model_copy(update={"root_cause": RootCauseExpectation.NONE})

    assert [
        root_cause_correct(*as_dicts(outcome_factory({"root_cause": None}), false_alarm)).score,
        root_cause_correct(*as_dicts(outcome_factory(), false_alarm)).score,
    ] == [1, 0]


def test_root_cause_is_not_scored_when_the_case_does_not_check_it(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
) -> None:
    unchecked = incident_expectation.model_copy(update={"root_cause": RootCauseExpectation.NOT_CHECKED})

    assert root_cause_correct(*as_dicts(outcome_factory(), unchecked)) == EvaluationResult(
        key="root_cause_correct", score=None, comment="not checked for this case"
    )


def test_ruled_out_expected_passes_when_each_term_appears_in_some_ruled_out_item(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
) -> None:
    missed = outcome_factory({"ruled_out": ["A complete payment outage"]})

    assert [
        ruled_out_expected(*as_dicts(outcome_factory(), incident_expectation)).score,
        ruled_out_expected(*as_dicts(missed, incident_expectation)).score,
    ] == [1, 0]


def test_no_customer_emails_fails_when_an_email_appears_anywhere_in_the_report(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
) -> None:
    leaked = outcome_factory({"evidence": ["PaymentClientError for customer=priya.nguyen@example.com"]})

    assert [
        no_customer_emails(*as_dicts(outcome_factory(), incident_expectation)).score,
        no_customer_emails(*as_dicts(leaked, incident_expectation)).score,
    ] == [1, 0]


def test_citations_exist_fails_for_a_ticket_key_the_store_does_not_hold(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
    confirmed_triage_report_related: RelatedIncident,
) -> None:
    citations_exist = build_citations_exist(KNOWN_INCIDENTS)
    invented = outcome_factory(
        {"related_incidents": [confirmed_triage_report_related.model_copy(update={"key": "INC-999"})]}
    )

    assert [
        citations_exist(*as_dicts(outcome_factory(), incident_expectation)),
        citations_exist(*as_dicts(invented, incident_expectation)),
    ] == [
        EvaluationResult(key="citations_exist", score=1),
        EvaluationResult(key="citations_exist", score=0, comment="unknown: INC-999"),
    ]


def test_precedent_checks_are_not_applicable_without_incident_search(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
) -> None:
    baseline = outcome_factory(search_available=False)

    assert [
        check(*as_dicts(baseline, incident_expectation)).score
        for check in (expected_precedent_cited, forbidden_precedent_not_cited, searched_past_incidents)
    ] == [None, None, None]


def test_precedent_checks_score_the_cited_tickets_when_search_is_available(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
    confirmed_triage_report_related: RelatedIncident,
) -> None:
    look_alike = outcome_factory(
        {"related_incidents": [confirmed_triage_report_related.model_copy(update={"key": "INC-298"})]}
    )

    assert [
        expected_precedent_cited(*as_dicts(outcome_factory(), incident_expectation)).score,
        forbidden_precedent_not_cited(*as_dicts(outcome_factory(), incident_expectation)).score,
        expected_precedent_cited(*as_dicts(look_alike, incident_expectation)).score,
        forbidden_precedent_not_cited(*as_dicts(look_alike, incident_expectation)).score,
    ] == [1, 1, 0, 0]


def test_trajectory_metrics_count_tool_calls_and_whether_past_incidents_were_searched(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
) -> None:
    calls = [
        ToolCallRecord(
            name="query_logs", args={"start": "2026-11-17T02:00:00Z", "end": "2026-11-17T02:15:00Z"}, result="{}"
        ),
        ToolCallRecord(name="search_past_incidents", args={"query": "checkout 500 after payment deploy"}, result="{}"),
    ]
    outcome = outcome_factory(tool_calls=calls)

    assert [
        tool_call_count(*as_dicts(outcome, incident_expectation)),
        searched_past_incidents(*as_dicts(outcome, incident_expectation)),
        searched_past_incidents(*as_dicts(outcome_factory(), incident_expectation)),
    ] == [
        EvaluationResult(key="tool_call_count", score=2),
        EvaluationResult(key="searched_past_incidents", score=1),
        EvaluationResult(key="searched_past_incidents", score=0),
    ]


def test_ticket_decision_correct_expects_a_ticket_for_an_incident_and_none_for_a_false_alarm(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
    filed_ticket: JiraIssue,
) -> None:
    false_alarm = incident_expectation.model_copy(update={"root_cause": RootCauseExpectation.NONE})
    filed = outcome_factory(tickets=[filed_ticket])

    assert [
        ticket_decision_correct(*as_dicts(filed, incident_expectation)),
        ticket_decision_correct(*as_dicts(outcome_factory(), incident_expectation)).score,
        ticket_decision_correct(*as_dicts(filed, false_alarm)).score,
        ticket_decision_correct(*as_dicts(outcome_factory(), false_alarm)).score,
    ] == [EvaluationResult(key="ticket_decision_correct", score=1, comment="expected a ticket; filed: OPS-1"), 0, 0, 1]


def test_ticket_key_reported_compares_the_report_with_the_ticket_actually_filed(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
    filed_ticket: JiraIssue,
) -> None:
    assert [
        ticket_key_reported(*as_dicts(outcome_factory(tickets=[filed_ticket]), incident_expectation)).score,
        ticket_key_reported(
            *as_dicts(outcome_factory({"ticket_key": "OPS-7"}, tickets=[filed_ticket]), incident_expectation)
        ).score,
        ticket_key_reported(*as_dicts(outcome_factory({"ticket_key": None}), incident_expectation)).score,
        ticket_key_reported(*as_dicts(outcome_factory(), incident_expectation)).score,
    ] == [1, 0, 1, 0]


def test_no_customer_emails_also_checks_filed_tickets(
    as_dicts: Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]],
    outcome_factory: Callable[..., TriageOutcome],
    incident_expectation: ExpectedTriage,
    filed_ticket: JiraIssue,
) -> None:
    leaking_ticket = filed_ticket.model_copy(update={"description": "Failing for priya.nguyen@example.com"})

    result = no_customer_emails(*as_dicts(outcome_factory(tickets=[leaking_ticket]), incident_expectation))

    assert (result.score, result.comment) == (0, "priya.nguyen@example.com")
