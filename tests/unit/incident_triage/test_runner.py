from collections.abc import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolCall
from langchain_core.tools import StructuredTool

from incident_triage.agent.triage_agent import build_triage_agent
from incident_triage.models.triage_report import TriageReport
from incident_triage.runner import stream_triage
from incident_triage.settings import LLMProvider


ALERT = "ALR-8812: checkout-service 5xx error rate 18% since 02:09 UTC"
QUERY_ARGUMENTS = {"start": "2026-11-17T02:00:00Z", "end": "2026-11-17T02:30:00Z", "service": "checkout-service"}


def test_stream_yields_each_message_then_the_report(
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    query_logs_tool: StructuredTool,
    confirmed_triage_report: TriageReport,
) -> None:
    model = scripted_chat_model_factory(
        AIMessage(content="", tool_calls=[ToolCall(name="query_logs", args=QUERY_ARGUMENTS, id="call_1")]),
        report_submission_factory(confirmed_triage_report),
    )
    agent = build_triage_agent(model, [query_logs_tool], LLMProvider.ANTHROPIC)

    items = list(stream_triage(agent, ALERT, max_steps=10))

    assert [item if isinstance(item, TriageReport) else (item.type, item.content) for item in items] == [
        ("ai", ""),
        ("tool", query_logs_tool.invoke(QUERY_ARGUMENTS)),
        ("ai", confirmed_triage_report.model_dump_json()),
        confirmed_triage_report,
    ]


def test_stream_ends_with_explanation_when_final_answer_is_not_a_valid_report(
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    query_logs_tool: StructuredTool,
) -> None:
    model = scripted_chat_model_factory(AIMessage(content="Root cause: payment-service."))
    agent = build_triage_agent(model, [query_logs_tool], LLMProvider.ANTHROPIC)

    last_item = list(stream_triage(agent, ALERT, max_steps=10))[-1]

    assert (last_item.type, last_item.content.split(": ")[0]) == ("ai", "Triage ended without a valid report")


def test_stream_ends_with_explanation_when_agent_exceeds_step_limit(
    query_logs_tool: StructuredTool,
    scripted_chat_model_factory: Callable[..., BaseChatModel],
) -> None:
    model = scripted_chat_model_factory(
        *(
            AIMessage(content="", tool_calls=[ToolCall(name="query_logs", args=QUERY_ARGUMENTS, id=f"call_{index}")])
            for index in range(50)
        )
    )
    agent = build_triage_agent(model, [query_logs_tool], LLMProvider.ANTHROPIC)

    last_item = list(stream_triage(agent, ALERT, max_steps=4))[-1]

    assert (last_item.type, last_item.content) == (
        "ai",
        "Triage stopped after 4 steps without reaching a conclusion.",
    )
