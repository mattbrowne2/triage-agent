from collections.abc import Callable, Sequence

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, ToolMessage
from langchain_core.tools import BaseTool
from pydantic import JsonValue

from evals.models import CaseInput, ToolCallRecord, TriageOutcome
from incident_triage.agent.triage_agent import build_triage_agent
from incident_triage.jira.store import JiraStore
from incident_triage.log_store.repository import LogRepository
from incident_triage.log_store.snapshot import snapshot
from incident_triage.models.datadog import LogArchive
from incident_triage.models.jira import JiraIssue
from incident_triage.models.tools import ToolName
from incident_triage.models.triage_report import TriageReport
from incident_triage.runner import stream_triage
from incident_triage.settings import LLMProvider
from incident_triage.tools.create_jira_ticket import build_create_jira_ticket_tool
from incident_triage.tools.query_logs import build_query_logs_tool
from incident_triage.tools.summarize_log_patterns import build_summarize_log_patterns_tool
from incident_triage.wiring import alert_key_for


type Target = Callable[[dict[str, JsonValue]], dict[str, JsonValue]]


def build_triage_target(
    model: BaseChatModel,
    archive: LogArchive,
    extra_tools: Sequence[BaseTool],
    provider: LLMProvider,
    max_steps: int,
) -> Target:
    search_available = any(tool.name == ToolName.SEARCH_PAST_INCIDENTS for tool in extra_tools)

    def run_case(inputs: dict[str, JsonValue]) -> dict[str, JsonValue]:
        case = CaseInput.model_validate(inputs)
        repository = LogRepository(snapshot(archive, case.as_of))
        jira = JiraStore(clock=lambda: case.as_of, issues=[])
        tools = [
            build_query_logs_tool(repository),
            build_summarize_log_patterns_tool(repository),
            *extra_tools,
            build_create_jira_ticket_tool(jira, alert_key_for(case.alert)),
        ]
        agent = build_triage_agent(model, tools, provider)
        try:
            items = list(stream_triage(agent, case.alert, max_steps))
        except Exception as error:
            failed = TriageOutcome(
                report=None,
                failure=f"{type(error).__name__}: {error}",
                tool_calls=[],
                incident_search_available=search_available,
                tickets=jira.issues(),
            )
            return failed.model_dump(mode="json")
        return _outcome(items, search_available, jira.issues()).model_dump(mode="json")

    return run_case


def _outcome(items: list[AnyMessage | TriageReport], search_available: bool, tickets: list[JiraIssue]) -> TriageOutcome:
    results = {item.tool_call_id: item.text for item in items if isinstance(item, ToolMessage)}
    tool_calls = [
        ToolCallRecord(
            name=call["name"],
            args=call["args"],
            result=results[call["id"]] if call["id"] in results else None,
        )
        for item in items
        if isinstance(item, AIMessage)
        for call in item.tool_calls
        if call["name"] != TriageReport.__name__
    ]
    match items[-1]:
        case TriageReport() as report:
            return TriageOutcome(
                report=report,
                failure=None,
                tool_calls=tool_calls,
                incident_search_available=search_available,
                tickets=tickets,
            )
        case message:
            return TriageOutcome(
                report=None,
                failure=message.text,
                tool_calls=tool_calls,
                incident_search_available=search_available,
                tickets=tickets,
            )
