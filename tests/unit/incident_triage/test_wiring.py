from pathlib import Path

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from incident_triage import wiring
from incident_triage.models.tools import ToolName
from incident_triage.settings import Settings


@pytest.mark.parametrize(
    ("search_enabled", "expected_tools"),
    [
        (
            True,
            [
                ToolName.QUERY_LOGS,
                ToolName.SUMMARIZE_LOG_PATTERNS,
                ToolName.SEARCH_PAST_INCIDENTS,
                ToolName.CREATE_JIRA_TICKET,
            ],
        ),
        (False, [ToolName.QUERY_LOGS, ToolName.SUMMARIZE_LOG_PATTERNS, ToolName.CREATE_JIRA_TICKET]),
    ],
)
def test_toolkit_adds_incident_search_only_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    fake_embeddings: DeterministicFakeEmbedding,
    search_enabled: bool,
    expected_tools: list[ToolName],
) -> None:
    monkeypatch.setattr(wiring, "build_embeddings", lambda settings: fake_embeddings)
    settings = Settings(INCIDENT_SEARCH_ENABLED=search_enabled, JIRA_TICKETS_PATH=tmp_path / "tickets.json")

    tools = wiring.AgentToolkit(settings).tools_for("alert-1")

    assert [tool.name for tool in tools] == expected_tools


def test_alert_key_for_free_text_alerts_is_stable_and_distinct() -> None:
    assert (
        wiring.alert_key_for("ALR-8812: checkout 5xx"),
        wiring.alert_key_for("ALR-8812: checkout 5xx") == wiring.alert_key_for("ALR-8813: checkout 5xx"),
    ) == (wiring.alert_key_for("ALR-8812: checkout 5xx"), False)
