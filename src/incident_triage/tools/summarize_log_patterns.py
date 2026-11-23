from langchain_core.tools import StructuredTool, ToolException
from pydantic import JsonValue

from incident_triage.log_store.errors import LogSearchError
from incident_triage.log_store.repository import LogRepository
from incident_triage.models.log_patterns import LogPatternQuery
from incident_triage.models.tools import ToolName
from incident_triage.tools.description_loader import load_tool_description


def build_summarize_log_patterns_tool(repository: LogRepository) -> StructuredTool:
    def summarize_log_patterns(**arguments: JsonValue) -> str:
        try:
            return repository.summarize(LogPatternQuery.model_validate(arguments)).model_dump_json()
        except LogSearchError as error:
            raise ToolException(str(error)) from error

    return StructuredTool.from_function(
        func=summarize_log_patterns,
        name=ToolName.SUMMARIZE_LOG_PATTERNS,
        description=load_tool_description(ToolName.SUMMARIZE_LOG_PATTERNS),
        args_schema=LogPatternQuery,
        handle_tool_error=True,
    )
