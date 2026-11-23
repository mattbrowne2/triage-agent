from collections.abc import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolCall
from langchain_core.tools import StructuredTool

from evals.models import ToolCallRecord, TriageOutcome
from evals.target import build_triage_target
from incident_triage.models.datadog import Log, LogArchive
from incident_triage.models.jira import TicketRequest
from incident_triage.models.log_search import LogSearchMeta, LogSearchResponse
from incident_triage.models.triage_report import TriageReport
from incident_triage.settings import LLMProvider


WINDOW = {"start": "2026-11-17T02:00:00Z", "end": "2026-11-17T02:10:00Z"}
QUERY_ARGUMENTS = {"start": "2026-11-17T02:00:00Z", "end": "2026-11-17T02:30:00Z", "service": "checkout-service"}
CASE_INPUTS = {"alert": "ALR-8812: checkout-service 5xx since 02:09", "as_of": "2026-11-17T02:10:00Z"}


def test_target_records_tool_calls_with_results_from_logs_before_as_of_and_the_report(
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    report_tool_call_factory: Callable[[TriageReport], AIMessage],
    log_archive: LogArchive,
    checkout_order_info_log: Log,
    confirmed_triage_report: TriageReport,
) -> None:
    model = scripted_chat_model_factory(
        AIMessage(content="", tool_calls=[ToolCall(name="query_logs", args=QUERY_ARGUMENTS, id="call_1")]),
        report_tool_call_factory(confirmed_triage_report),
    )
    target = build_triage_target(model, log_archive, [], LLMProvider.OPENAI, max_steps=10)

    outputs = target(CASE_INPUTS)

    assert outputs == TriageOutcome(
        report=confirmed_triage_report,
        failure=None,
        tool_calls=[
            ToolCallRecord(
                name="query_logs",
                args=QUERY_ARGUMENTS,
                result=LogSearchResponse(
                    data=[checkout_order_info_log], meta=LogSearchMeta(total_matches=1)
                ).model_dump_json(),
            )
        ],
        incident_search_available=False,
        tickets=[],
    ).model_dump(mode="json")


def test_target_reports_incident_search_as_available_when_its_tool_is_given(
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    log_archive: LogArchive,
    search_past_incidents_tool: StructuredTool,
    confirmed_triage_report: TriageReport,
) -> None:
    model = scripted_chat_model_factory(report_submission_factory(confirmed_triage_report))
    target = build_triage_target(model, log_archive, [search_past_incidents_tool], LLMProvider.ANTHROPIC, 10)

    assert target(CASE_INPUTS)["incident_search_available"] is True


def test_target_records_the_runner_failure_when_no_report_is_produced(
    scripted_chat_model_factory: Callable[..., BaseChatModel], log_archive: LogArchive
) -> None:
    model = scripted_chat_model_factory(
        *(
            AIMessage(content="", tool_calls=[ToolCall(name="query_logs", args=QUERY_ARGUMENTS, id=f"call_{index}")])
            for index in range(10)
        )
    )
    target = build_triage_target(model, log_archive, [], LLMProvider.ANTHROPIC, max_steps=4)

    outputs = target(CASE_INPUTS)

    assert (outputs["report"], outputs["failure"]) == (
        None,
        "Triage stopped after 4 steps without reaching a conclusion.",
    )


def test_target_records_provider_errors_as_failures(
    unreachable_chat_model: BaseChatModel, log_archive: LogArchive
) -> None:
    target = build_triage_target(unreachable_chat_model, log_archive, [], LLMProvider.ANTHROPIC, max_steps=10)

    outputs = target(CASE_INPUTS)

    assert (outputs["report"], outputs["failure"]) == (None, "ConnectionError: provider unreachable")


def test_target_records_no_result_for_a_tool_call_cut_off_by_the_step_limit(
    scripted_chat_model_factory: Callable[..., BaseChatModel], log_archive: LogArchive
) -> None:
    model = scripted_chat_model_factory(
        *(
            AIMessage(content="", tool_calls=[ToolCall(name="query_logs", args=QUERY_ARGUMENTS, id=f"call_{index}")])
            for index in range(10)
        )
    )
    target = build_triage_target(model, log_archive, [], LLMProvider.ANTHROPIC, max_steps=3)

    tool_calls = target(CASE_INPUTS)["tool_calls"]

    assert [call["result"] is None for call in tool_calls] == [False, True]


def test_target_gives_each_case_pattern_summary_and_a_fresh_ticket_store_dated_at_as_of(
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    log_archive: LogArchive,
    rollback_ticket_request: TicketRequest,
    confirmed_triage_report: TriageReport,
) -> None:
    def scripted_case() -> list[AIMessage]:
        return [
            AIMessage(
                content="",
                tool_calls=[
                    ToolCall(name="summarize_log_patterns", args=WINDOW, id="call_summary"),
                    ToolCall(
                        name="create_jira_ticket",
                        args=rollback_ticket_request.model_dump(mode="json"),
                        id="call_ticket",
                    ),
                ],
            ),
            report_submission_factory(confirmed_triage_report),
        ]

    model = scripted_chat_model_factory(*scripted_case(), *scripted_case())
    target = build_triage_target(model, log_archive, [], LLMProvider.ANTHROPIC, max_steps=10)

    first, second = target(CASE_INPUTS), target(CASE_INPUTS)

    assert (
        [call["name"] for call in first["tool_calls"]],
        [(ticket["key"], ticket["created_at"]) for ticket in first["tickets"]],
        [ticket["key"] for ticket in second["tickets"]],
    ) == (
        ["summarize_log_patterns", "create_jira_ticket"],
        [("OPS-1", "2026-11-17T02:10:00Z")],
        ["OPS-1"],
    )
