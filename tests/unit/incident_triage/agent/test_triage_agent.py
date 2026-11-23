from collections.abc import Callable

import pytest
from langchain.agents.structured_output import ProviderStrategy, StructuredOutputValidationError
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolCall
from langchain_core.tools import StructuredTool

from incident_triage.agent.response_format import REPORT_SUBMITTED
from incident_triage.agent.triage_agent import build_triage_agent
from incident_triage.log_store.repository import LogRepository
from incident_triage.models.log_search import LogSearchQuery
from incident_triage.models.triage_report import TriageReport
from incident_triage.settings import LLMProvider


ALERT = "ALR-8812: checkout-service 5xx error rate 18% since 02:09 UTC"


def test_agent_queries_logs_then_answers_with_a_structured_report(
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    query_logs_tool: StructuredTool,
    log_repository: LogRepository,
    confirmed_triage_report: TriageReport,
) -> None:
    query_arguments = {"start": "2026-11-17T02:00:00Z", "end": "2026-11-17T02:30:00Z", "status": "error"}
    model = scripted_chat_model_factory(
        AIMessage(content="", tool_calls=[ToolCall(name="query_logs", args=query_arguments, id="call_1")]),
        report_submission_factory(confirmed_triage_report),
    )
    agent = build_triage_agent(model, [query_logs_tool], LLMProvider.ANTHROPIC)

    result = agent.invoke({"messages": [HumanMessage(content=ALERT)]})

    assert (
        [(message.type, message.content) for message in result["messages"]],
        result["structured_response"],
    ) == (
        [
            ("human", ALERT),
            ("ai", ""),
            ("tool", log_repository.search(LogSearchQuery.model_validate(query_arguments)).model_dump_json()),
            ("ai", confirmed_triage_report.model_dump_json()),
        ],
        confirmed_triage_report,
    )


def test_agent_receives_tool_errors_it_can_correct(
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    query_logs_tool: StructuredTool,
    confirmed_triage_report: TriageReport,
) -> None:
    swapped_window = {"start": "2026-11-17T02:30:00Z", "end": "2026-11-17T02:00:00Z"}
    model = scripted_chat_model_factory(
        AIMessage(content="", tool_calls=[ToolCall(name="query_logs", args=swapped_window, id="call_1")]),
        report_submission_factory(confirmed_triage_report),
    )
    agent = build_triage_agent(model, [query_logs_tool], LLMProvider.ANTHROPIC)

    result = agent.invoke({"messages": [HumanMessage(content=ALERT)]})

    assert [(message.type, message.content) for message in result["messages"]][2] == (
        "tool",
        "Invalid time window: end 2026-11-17T02:00:00+00:00 must be after start 2026-11-17T02:30:00+00:00",
    )


def test_model_gets_native_structured_output_without_forced_tool_use(
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    query_logs_tool: StructuredTool,
    confirmed_triage_report: TriageReport,
) -> None:
    model = scripted_chat_model_factory(report_submission_factory(confirmed_triage_report))
    agent = build_triage_agent(model, [query_logs_tool], LLMProvider.ANTHROPIC)

    agent.invoke({"messages": [HumanMessage(content=ALERT)]})

    assert model.bound_kwargs == ProviderStrategy(TriageReport).to_model_kwargs()


def test_final_answer_that_is_not_a_report_raises_structured_output_error(
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    query_logs_tool: StructuredTool,
) -> None:
    model = scripted_chat_model_factory(AIMessage(content="Root cause: payment-service."))
    agent = build_triage_agent(model, [query_logs_tool], LLMProvider.ANTHROPIC)

    with pytest.raises(StructuredOutputValidationError):
        agent.invoke({"messages": [HumanMessage(content=ALERT)]})


def test_openai_agent_submits_the_report_as_a_forced_tool_call(
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    report_tool_call_factory: Callable[[TriageReport], AIMessage],
    query_logs_tool: StructuredTool,
    confirmed_triage_report: TriageReport,
) -> None:
    model = scripted_chat_model_factory(report_tool_call_factory(confirmed_triage_report))
    agent = build_triage_agent(model, [query_logs_tool], LLMProvider.OPENAI)

    result = agent.invoke({"messages": [HumanMessage(content=ALERT)]})

    assert (
        [(message.type, message.content) for message in result["messages"]],
        result["structured_response"],
        model.bound_kwargs,
    ) == (
        [("human", ALERT), ("ai", ""), ("tool", REPORT_SUBMITTED)],
        confirmed_triage_report,
        {"tool_choice": "any"},
    )


def test_openai_agent_is_told_why_an_invalid_report_was_rejected_and_can_resubmit(
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    report_tool_call_factory: Callable[[TriageReport], AIMessage],
    query_logs_tool: StructuredTool,
    confirmed_triage_report: TriageReport,
) -> None:
    incomplete_report = AIMessage(
        content="", tool_calls=[ToolCall(name="TriageReport", args={"root_cause": "unknown"}, id="report_0")]
    )
    model = scripted_chat_model_factory(incomplete_report, report_tool_call_factory(confirmed_triage_report))
    agent = build_triage_agent(model, [query_logs_tool], LLMProvider.OPENAI)

    result = agent.invoke({"messages": [HumanMessage(content=ALERT)]})

    assert (result["messages"][2].type, "alert_confirmed" in result["messages"][2].content) == ("tool", True)
    assert result["structured_response"] == confirmed_triage_report
