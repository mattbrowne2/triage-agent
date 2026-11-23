from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256

from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from incident_triage.agent.chat_model import build_chat_model
from incident_triage.agent.triage_agent import build_triage_agent
from incident_triage.incident_store.embeddings import build_embeddings
from incident_triage.incident_store.index import IncidentIndex
from incident_triage.jira.store import FileJiraStore
from incident_triage.log_store.repository import LogRepository
from incident_triage.settings import Settings
from incident_triage.tools.create_jira_ticket import build_create_jira_ticket_tool
from incident_triage.tools.query_logs import build_query_logs_tool
from incident_triage.tools.search_past_incidents import build_search_past_incidents_tool
from incident_triage.tools.summarize_log_patterns import build_summarize_log_patterns_tool


type AgentFactory = Callable[[str], CompiledStateGraph]


def alert_key_for(alert_text: str) -> str:
    return f"alert:{sha256(alert_text.encode()).hexdigest()[:12]}"


def incident_tools(settings: Settings) -> list[BaseTool]:
    match settings.INCIDENT_SEARCH_ENABLED:
        case False:
            return []
        case True:
            index = IncidentIndex.from_file(
                settings.INCIDENTS_PATH, build_embeddings(settings), settings.INCIDENT_MIN_SIMILARITY
            )
            return [build_search_past_incidents_tool(index)]


class AgentToolkit:
    def __init__(self, settings: Settings) -> None:
        self._repository = LogRepository.from_file(settings.DATADOG_LOGS_PATH)
        self._incident_tools = incident_tools(settings)
        self._jira = FileJiraStore(settings.JIRA_TICKETS_PATH, clock=lambda: datetime.now(UTC))

    def tools_for(self, alert_key: str) -> list[BaseTool]:
        return [
            build_query_logs_tool(self._repository),
            build_summarize_log_patterns_tool(self._repository),
            *self._incident_tools,
            build_create_jira_ticket_tool(self._jira, alert_key),
        ]


def build_agent_factory(settings: Settings) -> AgentFactory:
    toolkit = AgentToolkit(settings)
    model = build_chat_model(settings)

    def build_agent(alert_key: str) -> CompiledStateGraph:
        return build_triage_agent(model, toolkit.tools_for(alert_key), settings.LLM_PROVIDER)

    return build_agent
