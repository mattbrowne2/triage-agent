from pydantic import AwareDatetime, BaseModel, Field

from incident_triage.models.datadog import LogStatus


class LogPatternQuery(BaseModel):
    start: AwareDatetime = Field(description="Inclusive start of the time window, ISO 8601 with timezone")
    end: AwareDatetime = Field(description="Exclusive end of the time window, ISO 8601 with timezone")


class LogPattern(BaseModel):
    service: str
    status: LogStatus
    template: str
    count: int
    first_seen: AwareDatetime
    last_seen: AwareDatetime


class LogPatternSummary(BaseModel):
    total_logs: int
    patterns: list[LogPattern]
