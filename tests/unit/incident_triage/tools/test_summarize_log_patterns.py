from pathlib import Path

from langchain_core.tools import StructuredTool

from incident_triage.log_store.repository import LogRepository
from incident_triage.models.log_patterns import LogPatternQuery
from incident_triage.models.tools import ToolName


DESCRIPTIONS_DIR = Path(__file__).parents[4] / "src" / "incident_triage" / "tools" / "descriptions"
WINDOW = {"start": "2026-11-17T02:00:00Z", "end": "2026-11-17T02:30:00Z"}


def test_tool_exposes_name_description_and_argument_schema(summarize_log_patterns_tool: StructuredTool) -> None:
    assert (
        summarize_log_patterns_tool.name,
        summarize_log_patterns_tool.description,
        summarize_log_patterns_tool.args_schema,
    ) == (
        ToolName.SUMMARIZE_LOG_PATTERNS,
        (DESCRIPTIONS_DIR / "summarize_log_patterns.md").read_text().strip(),
        LogPatternQuery,
    )


def test_tool_returns_the_pattern_summary_as_json(
    summarize_log_patterns_tool: StructuredTool, log_repository: LogRepository
) -> None:
    assert (
        summarize_log_patterns_tool.invoke(WINDOW)
        == log_repository.summarize(LogPatternQuery.model_validate(WINDOW)).model_dump_json()
    )


def test_tool_returns_invalid_time_window_error_to_the_agent(summarize_log_patterns_tool: StructuredTool) -> None:
    result = summarize_log_patterns_tool.invoke({"start": WINDOW["end"], "end": WINDOW["start"]})

    assert result == (
        "Invalid time window: end 2026-11-17T02:00:00+00:00 must be after start 2026-11-17T02:30:00+00:00"
    )
