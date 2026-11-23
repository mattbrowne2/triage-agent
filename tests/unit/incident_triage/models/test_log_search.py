from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from incident_triage.models.log_search import LogSearchQuery


def test_query_without_timezone_raises_validation_error() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        LogSearchQuery.model_validate({"start": "2026-11-17T02:00:00", "end": "2026-11-17T02:30:00"})


def test_query_parses_iso_timestamps_from_tool_call_arguments() -> None:
    query = LogSearchQuery.model_validate({"start": "2026-11-17T02:00:00Z", "end": "2026-11-17T02:30:00Z"})

    assert query == LogSearchQuery(
        start=datetime(2026, 11, 17, 2, 0, tzinfo=UTC),
        end=datetime(2026, 11, 17, 2, 30, tzinfo=UTC),
        service=None,
        status=None,
        message_contains=None,
        limit=25,
    )
