from enum import StrEnum, auto

from pydantic import BaseModel, ConfigDict, Field


class Confidence(StrEnum):
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()


class RelatedIncident(BaseModel):
    key: str = Field(description="Ticket key exactly as search_past_incidents returned it, such as INC-311")
    why_similar: str = Field(description="What the past incident and this one have in common, from the current logs")
    what_differs: str = Field(description="How this incident differs, such as a different field, version or service")
    change_urls: list[str] = Field(description="Links to the changes that fixed the past incident, copied exactly")


class TriageReport(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"description": "The final triage report, given once the investigation is complete."}
    )

    alert_confirmed: bool = Field(
        description="True if the logs show the incident the alert describes and contradict none of its claims: the "
        "affected service, the symptom, and a start time if the alert states one. A claim the logs cannot check, such "
        "as a rate that needs request counts, is not a contradiction, and neither is a detail the alert doesn't "
        "state. False only if the logs contradict a claim or show no incident."
    )
    alert_discrepancy: str | None = Field(
        description="What the alert got wrong according to the logs. Null when alert_confirmed is true."
    )
    root_cause: str | None = Field(
        description="The most likely root cause. Null when the evidence does not support one."
    )
    confidence: Confidence = Field(description="Confidence in the root cause, or in there being no incident")
    evidence: list[str] = Field(
        description="Log messages, timestamps, services and trace IDs that support the conclusion"
    )
    impact: str = Field(description="What is affected and since when")
    next_steps: list[str] = Field(description="Recommended actions for the on-call engineer")
    ruled_out: list[str] = Field(description="Candidate causes the logs ruled out, such as pre-existing noise")
    related_incidents: list[RelatedIncident] = Field(
        description="Past incidents from search_past_incidents that resemble this one. Empty if the search found none "
        "or none fit the current logs. Cite only incidents the search returned."
    )
    ticket_key: str | None = Field(
        description="Key of the Jira ticket you filed with create_jira_ticket, such as OPS-1, or null if you filed none"
    )
