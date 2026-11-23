from pathlib import Path

import pytest
from langchain_core.tools import StructuredTool
from pydantic import ValidationError

from incident_triage.models.datadog import Log
from incident_triage.models.log_search import LogSearchMeta, LogSearchQuery, LogSearchResponse
from incident_triage.models.tools import ToolName


DESCRIPTIONS_DIR = Path(__file__).parents[4] / "src" / "incident_triage" / "tools" / "descriptions"


def test_tool_exposes_name_description_and_argument_schema(query_logs_tool: StructuredTool) -> None:
    assert (query_logs_tool.name, query_logs_tool.description, query_logs_tool.args_schema) == (
        ToolName.QUERY_LOGS,
        (DESCRIPTIONS_DIR / "query_logs.md").read_text().strip(),
        LogSearchQuery,
    )


def test_tool_returns_matching_logs_as_datadog_style_json(
    query_logs_tool: StructuredTool, checkout_payment_error_log: Log
) -> None:
    result = query_logs_tool.invoke(
        {
            "start": "2026-11-17T02:00:00Z",
            "end": "2026-11-17T02:30:00Z",
            "service": "checkout-service",
            "status": "error",
        }
    )

    assert (
        result
        == LogSearchResponse(data=[checkout_payment_error_log], meta=LogSearchMeta(total_matches=1)).model_dump_json()
    )


def test_tool_returns_unknown_service_error_to_the_agent(query_logs_tool: StructuredTool) -> None:
    result = query_logs_tool.invoke(
        {"start": "2026-11-17T02:00:00Z", "end": "2026-11-17T02:30:00Z", "service": "payments"}
    )

    assert result == "Unknown service 'payments'. Known services: checkout-service, payment-service"


def test_tool_returns_invalid_time_window_error_to_the_agent(query_logs_tool: StructuredTool) -> None:
    result = query_logs_tool.invoke({"start": "2026-11-17T02:30:00Z", "end": "2026-11-17T02:00:00Z"})

    assert result == (
        "Invalid time window: end 2026-11-17T02:00:00+00:00 must be after start 2026-11-17T02:30:00+00:00"
    )


def test_tool_rejects_arguments_that_do_not_match_its_schema(query_logs_tool: StructuredTool) -> None:
    with pytest.raises(ValidationError):
        query_logs_tool.invoke({"start": "2026-11-17T02:00:00", "end": "2026-11-17T02:30:00Z"})
