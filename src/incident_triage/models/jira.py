from enum import StrEnum

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class JiraPriority(StrEnum):
    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class TicketRequest(BaseModel):
    summary: str = Field(
        min_length=10, max_length=120, description="One line an engineer can act on: the symptom and likely cause"
    )
    description: str = Field(
        description="Alert, impact, root cause with confidence, key evidence (timestamps, versions, trace IDs), "
        "what was ruled out, related past incidents, and recommended next steps"
    )
    priority: JiraPriority = Field(
        description="Highest when customers are failing now, High for degraded service, Medium or Low otherwise"
    )
    service: str = Field(description="The service whose owners need to act, usually the one with the root cause")


class JiraIssue(BaseModel):
    id: str
    key: str
    summary: str
    description: str
    priority: JiraPriority
    service: str
    alert_key: str
    created_at: AwareDatetime


class JiraCreateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    key: str
    self_url: str = Field(alias="self")


class JiraIssueArchive(BaseModel):
    issues: list[JiraIssue]
