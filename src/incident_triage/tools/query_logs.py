from langchain_core.tools import StructuredTool, ToolException
from pydantic import JsonValue

from incident_triage.log_store.errors import LogSearchError
from incident_triage.log_store.repository import LogRepository
from incident_triage.models.log_search import LogSearchQuery
from incident_triage.models.tools import ToolName
from incident_triage.tools.description_loader import load_tool_description


def build_query_logs_tool(repository: LogRepository) -> StructuredTool:
    def query_logs(**arguments: JsonValue) -> str:
        try:
            return repository.search(LogSearchQuery.model_validate(arguments)).model_dump_json()
        except LogSearchError as error:
            raise ToolException(str(error)) from error

    return StructuredTool.from_function(
        func=query_logs,
        name=ToolName.QUERY_LOGS,
        description=load_tool_description(ToolName.QUERY_LOGS),
        args_schema=LogSearchQuery,
        handle_tool_error=True,
    )
