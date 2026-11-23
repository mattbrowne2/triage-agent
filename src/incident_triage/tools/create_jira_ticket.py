from langchain_core.tools import StructuredTool, ToolException
from pydantic import JsonValue

from incident_triage.jira.errors import JiraError
from incident_triage.jira.store import JiraStore
from incident_triage.models.jira import JiraCreateResponse, TicketRequest
from incident_triage.models.tools import ToolName
from incident_triage.tools.description_loader import load_tool_description


JIRA_BASE_URL = "https://jira.example.com"


def build_create_jira_ticket_tool(store: JiraStore, alert_key: str) -> StructuredTool:
    def create_jira_ticket(**arguments: JsonValue) -> str:
        try:
            issue, _ = store.create(alert_key, TicketRequest.model_validate(arguments))
        except JiraError as error:
            raise ToolException(str(error)) from error
        response = JiraCreateResponse(
            id=issue.id, key=issue.key, self_url=f"{JIRA_BASE_URL}/rest/api/3/issue/{issue.id}"
        )
        return response.model_dump_json(by_alias=True)

    return StructuredTool.from_function(
        func=create_jira_ticket,
        name=ToolName.CREATE_JIRA_TICKET,
        description=load_tool_description(ToolName.CREATE_JIRA_TICKET),
        args_schema=TicketRequest,
        handle_tool_error=True,
    )
