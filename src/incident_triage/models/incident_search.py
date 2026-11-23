from pydantic import BaseModel, Field

from incident_triage.models.incident import PastIncident


class IncidentSearchQuery(BaseModel):
    query: str = Field(
        min_length=3,
        description="What the current incident looks like: error messages, affected services, and what changed "
        "just before it started",
    )
    limit: int = Field(default=3, ge=1, le=10, description="Maximum number of past incidents to return")


class IncidentMatch(BaseModel):
    similarity: float
    incident: PastIncident


class IncidentSearchResponse(BaseModel):
    matches: list[IncidentMatch]
