from enum import StrEnum, auto

from pydantic import BaseModel

from incident_triage.models.alert import Alert
from incident_triage.models.triage_report import TriageReport


class TriageStatus(StrEnum):
    QUEUED = auto()
    COMPLETED = auto()
    FAILED = auto()


class Triage(BaseModel):
    alert: Alert
    status: TriageStatus = TriageStatus.QUEUED
    report: TriageReport | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str = "ok"


class VersionResponse(BaseModel):
    version: str
