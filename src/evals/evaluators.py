from collections.abc import Callable

from langsmith.evaluation import EvaluationResult
from pydantic import JsonValue

from evals.models import ExpectedTriage, RootCauseExpectation, TriageOutcome
from incident_triage.models.tools import ToolName
from incident_triage.pii import find_emails


type Evaluator = Callable[[dict[str, JsonValue], dict[str, JsonValue]], EvaluationResult]


def report_produced(outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]) -> EvaluationResult:
    outcome = TriageOutcome.model_validate(outputs)
    match outcome.report:
        case None:
            return EvaluationResult(key="report_produced", score=0, comment=outcome.failure)
        case _:
            return EvaluationResult(key="report_produced", score=1)


def alert_confirmed_correct(outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]) -> EvaluationResult:
    outcome, expected = _parse(outputs, reference_outputs)
    match outcome.report:
        case None:
            return EvaluationResult(key="alert_confirmed_correct", score=0, comment="no report")
        case report:
            return EvaluationResult(
                key="alert_confirmed_correct",
                score=int(report.alert_confirmed == expected.alert_confirmed),
                comment=f"expected {expected.alert_confirmed}, got {report.alert_confirmed}",
            )


def root_cause_correct(outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]) -> EvaluationResult:
    outcome, expected = _parse(outputs, reference_outputs)
    match expected.root_cause, outcome.report:
        case RootCauseExpectation.NOT_CHECKED, _:
            return EvaluationResult(key="root_cause_correct", score=None, comment="not checked for this case")
        case _, None:
            return EvaluationResult(key="root_cause_correct", score=0, comment="no report")
        case RootCauseExpectation.NONE, report:
            return EvaluationResult(
                key="root_cause_correct", score=int(report.root_cause is None), comment=report.root_cause
            )
        case _, report:
            return _root_cause_names_terms(report.root_cause, expected.root_cause_terms)


def ruled_out_expected(outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]) -> EvaluationResult:
    outcome, expected = _parse(outputs, reference_outputs)
    match expected.ruled_out_terms, outcome.report:
        case [], _:
            return EvaluationResult(key="ruled_out_expected", score=None, comment="nothing to rule out for this case")
        case _, None:
            return EvaluationResult(key="ruled_out_expected", score=0, comment="no report")
        case terms, report:
            ruled_out = [item.lower() for item in report.ruled_out]
            found = all(any(term.lower() in item for item in ruled_out) for term in terms)
            return EvaluationResult(key="ruled_out_expected", score=int(found), comment=" | ".join(report.ruled_out))


def no_customer_emails(outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]) -> EvaluationResult:
    outcome = TriageOutcome.model_validate(outputs)
    written = [ticket.model_dump_json() for ticket in outcome.tickets]
    match outcome.report:
        case None if not written:
            return EvaluationResult(key="no_customer_emails", score=None, comment="nothing written")
        case None:
            leaked = find_emails("\n".join(written))
        case report:
            leaked = find_emails("\n".join([report.model_dump_json(), *written]))
    return EvaluationResult(
        key="no_customer_emails", score=int(not leaked), comment=", ".join(leaked) if leaked else None
    )


def ticket_decision_correct(outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]) -> EvaluationResult:
    outcome, expected = _parse(outputs, reference_outputs)
    ticket_expected = expected.root_cause != RootCauseExpectation.NONE
    filed = [ticket.key for ticket in outcome.tickets]
    return EvaluationResult(
        key="ticket_decision_correct",
        score=int(bool(filed) == ticket_expected),
        comment=f"expected {'a ticket' if ticket_expected else 'no ticket'}; filed: {', '.join(filed) or 'none'}",
    )


def ticket_key_reported(outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]) -> EvaluationResult:
    outcome = TriageOutcome.model_validate(outputs)
    filed = outcome.tickets[0].key if outcome.tickets else None
    match outcome.report:
        case None:
            return EvaluationResult(key="ticket_key_reported", score=None, comment="no report")
        case report:
            return EvaluationResult(
                key="ticket_key_reported",
                score=int(report.ticket_key == filed),
                comment=f"report: {report.ticket_key}, filed: {filed}",
            )


def build_citations_exist(known_incident_keys: frozenset[str]) -> Evaluator:
    def citations_exist(outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]) -> EvaluationResult:
        outcome = TriageOutcome.model_validate(outputs)
        match outcome.report:
            case None:
                return EvaluationResult(key="citations_exist", score=None, comment="no report")
            case report:
                unknown = [item.key for item in report.related_incidents if item.key not in known_incident_keys]
                return EvaluationResult(
                    key="citations_exist",
                    score=int(not unknown),
                    comment=f"unknown: {', '.join(unknown)}" if unknown else None,
                )

    return citations_exist


def expected_precedent_cited(
    outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]
) -> EvaluationResult:
    outcome, expected = _parse(outputs, reference_outputs)
    match outcome.incident_search_available, expected.related_incident, outcome.report:
        case False, _, _:
            return EvaluationResult(key="expected_precedent_cited", score=None, comment="no incident search")
        case _, None, _:
            return EvaluationResult(key="expected_precedent_cited", score=None, comment="no precedent expected")
        case _, _, None:
            return EvaluationResult(key="expected_precedent_cited", score=0, comment="no report")
        case _, key, report:
            cited = [item.key for item in report.related_incidents]
            return EvaluationResult(
                key="expected_precedent_cited", score=int(key in cited), comment=f"cited: {', '.join(cited)}"
            )


def forbidden_precedent_not_cited(
    outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]
) -> EvaluationResult:
    outcome, expected = _parse(outputs, reference_outputs)
    match outcome.incident_search_available, outcome.report:
        case False, _:
            return EvaluationResult(key="forbidden_precedent_not_cited", score=None, comment="no incident search")
        case _, None:
            return EvaluationResult(key="forbidden_precedent_not_cited", score=None, comment="no report")
        case _, report:
            cited = {item.key for item in report.related_incidents}
            forbidden = [key for key in expected.must_not_cite if key in cited]
            return EvaluationResult(
                key="forbidden_precedent_not_cited",
                score=int(not forbidden),
                comment=f"cited: {', '.join(forbidden)}" if forbidden else None,
            )


def tool_call_count(outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]) -> EvaluationResult:
    return EvaluationResult(key="tool_call_count", score=len(TriageOutcome.model_validate(outputs).tool_calls))


def searched_past_incidents(outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]) -> EvaluationResult:
    outcome = TriageOutcome.model_validate(outputs)
    match outcome.incident_search_available:
        case False:
            return EvaluationResult(key="searched_past_incidents", score=None, comment="no incident search")
        case True:
            searched = any(call.name == ToolName.SEARCH_PAST_INCIDENTS for call in outcome.tool_calls)
            return EvaluationResult(key="searched_past_incidents", score=int(searched))


def build_evaluators(known_incident_keys: frozenset[str]) -> list[Evaluator]:
    return [
        report_produced,
        alert_confirmed_correct,
        root_cause_correct,
        ruled_out_expected,
        no_customer_emails,
        ticket_decision_correct,
        ticket_key_reported,
        expected_precedent_cited,
        forbidden_precedent_not_cited,
        tool_call_count,
        searched_past_incidents,
        build_citations_exist(known_incident_keys),
    ]


def _root_cause_names_terms(root_cause: str | None, terms: list[str]) -> EvaluationResult:
    match root_cause:
        case None:
            return EvaluationResult(key="root_cause_correct", score=0, comment="no root cause given")
        case text:
            named = all(term.lower() in text.lower() for term in terms)
            return EvaluationResult(key="root_cause_correct", score=int(named), comment=text)


def _parse(
    outputs: dict[str, JsonValue], reference_outputs: dict[str, JsonValue]
) -> tuple[TriageOutcome, ExpectedTriage]:
    return TriageOutcome.model_validate(outputs), ExpectedTriage.model_validate(reference_outputs)
