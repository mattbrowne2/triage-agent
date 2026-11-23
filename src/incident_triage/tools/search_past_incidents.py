from langchain_core.tools import StructuredTool
from pydantic import JsonValue

from incident_triage.incident_store.index import IncidentIndex
from incident_triage.models.incident_search import IncidentSearchQuery
from incident_triage.models.tools import ToolName
from incident_triage.tools.description_loader import load_tool_description


def build_search_past_incidents_tool(index: IncidentIndex) -> StructuredTool:
    def search_past_incidents(**arguments: JsonValue) -> str:
        return index.search(IncidentSearchQuery.model_validate(arguments)).model_dump_json()

    return StructuredTool.from_function(
        func=search_past_incidents,
        name=ToolName.SEARCH_PAST_INCIDENTS,
        description=load_tool_description(ToolName.SEARCH_PAST_INCIDENTS),
        args_schema=IncidentSearchQuery,
        handle_tool_error=True,
    )
