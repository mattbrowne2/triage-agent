from collections.abc import Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolCall
from langchain_core.tools import StructuredTool

from incident_triage.agent.triage_agent import build_triage_agent
from incident_triage.models.alert import Alert
from incident_triage.models.triage_report import TriageReport
from incident_triage.settings import LLMProvider
from triage_api.models import Triage, TriageStatus
from triage_api.store import TriageStore
from triage_api.worker import run_triage


QUERY_ARGUMENTS = {"start": "2026-11-17T02:00:00Z", "end": "2026-11-17T02:30:00Z", "service": "checkout-service"}


def test_run_triage_completes_with_the_agent_report(
    store_with_checkout_alert: TriageStore,
    checkout_error_rate_alert: Alert,
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    report_submission_factory: Callable[[TriageReport], AIMessage],
    query_logs_tool: StructuredTool,
    confirmed_triage_report: TriageReport,
) -> None:
    model = scripted_chat_model_factory(report_submission_factory(confirmed_triage_report))
    agent = build_triage_agent(model, [query_logs_tool], LLMProvider.ANTHROPIC)

    run_triage(agent, store_with_checkout_alert, checkout_error_rate_alert.id, max_steps=10)

    assert store_with_checkout_alert.get(checkout_error_rate_alert.id) == Triage(
        alert=checkout_error_rate_alert, status=TriageStatus.COMPLETED, report=confirmed_triage_report
    )


def test_run_triage_fails_with_runner_explanation_when_step_limit_is_reached(
    store_with_checkout_alert: TriageStore,
    checkout_error_rate_alert: Alert,
    scripted_chat_model_factory: Callable[..., BaseChatModel],
    query_logs_tool: StructuredTool,
) -> None:
    model = scripted_chat_model_factory(
        *(
            AIMessage(content="", tool_calls=[ToolCall(name="query_logs", args=QUERY_ARGUMENTS, id=f"call_{index}")])
            for index in range(10)
        )
    )
    agent = build_triage_agent(model, [query_logs_tool], LLMProvider.ANTHROPIC)

    run_triage(agent, store_with_checkout_alert, checkout_error_rate_alert.id, max_steps=4)

    assert store_with_checkout_alert.get(checkout_error_rate_alert.id) == Triage(
        alert=checkout_error_rate_alert,
        status=TriageStatus.FAILED,
        error="Triage stopped after 4 steps without reaching a conclusion.",
    )


def test_run_triage_fails_with_error_when_model_provider_is_unreachable(
    store_with_checkout_alert: TriageStore,
    checkout_error_rate_alert: Alert,
    unreachable_chat_model: BaseChatModel,
    query_logs_tool: StructuredTool,
) -> None:
    agent = build_triage_agent(unreachable_chat_model, [query_logs_tool], LLMProvider.ANTHROPIC)

    run_triage(agent, store_with_checkout_alert, checkout_error_rate_alert.id, max_steps=10)

    assert store_with_checkout_alert.get(checkout_error_rate_alert.id) == Triage(
        alert=checkout_error_rate_alert, status=TriageStatus.FAILED, error="ConnectionError: provider unreachable"
    )
