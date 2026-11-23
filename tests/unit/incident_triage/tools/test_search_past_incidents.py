from pathlib import Path

import pytest
from langchain_core.tools import StructuredTool
from pydantic import ValidationError

from incident_triage.incident_store.documents import incident_document
from incident_triage.models.incident import PastIncident
from incident_triage.models.incident_search import IncidentMatch, IncidentSearchQuery, IncidentSearchResponse
from incident_triage.models.tools import ToolName


DESCRIPTIONS_DIR = Path(__file__).parents[4] / "src" / "incident_triage" / "tools" / "descriptions"


def test_tool_exposes_name_description_and_argument_schema(search_past_incidents_tool: StructuredTool) -> None:
    assert (
        search_past_incidents_tool.name,
        search_past_incidents_tool.description,
        search_past_incidents_tool.args_schema,
    ) == (
        ToolName.SEARCH_PAST_INCIDENTS,
        (DESCRIPTIONS_DIR / "search_past_incidents.md").read_text().strip(),
        IncidentSearchQuery,
    )


def test_tool_returns_matching_incidents_with_their_resolution_as_json(
    search_past_incidents_tool: StructuredTool, resolved_contract_incident: PastIncident
) -> None:
    result = search_past_incidents_tool.invoke({"query": incident_document(resolved_contract_incident)})

    assert (
        result
        == IncidentSearchResponse(
            matches=[IncidentMatch(similarity=1.0, incident=resolved_contract_incident)]
        ).model_dump_json()
    )


def test_tool_returns_no_matches_when_nothing_is_similar_enough(search_past_incidents_tool: StructuredTool) -> None:
    result = search_past_incidents_tool.invoke({"query": "Kafka consumer lag in the billing pipeline"})

    assert result == IncidentSearchResponse(matches=[]).model_dump_json()


def test_tool_rejects_arguments_that_do_not_match_its_schema(search_past_incidents_tool: StructuredTool) -> None:
    with pytest.raises(ValidationError):
        search_past_incidents_tool.invoke({"query": "checkout 500s", "limit": 0})
