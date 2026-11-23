from pydantic import AwareDatetime, BaseModel, Field, JsonValue

from incident_triage.models.datadog import LogStatus


class LogStream(BaseModel):
    service: str
    status: LogStatus
    version: str
    messages: list[str] = Field(min_length=1)
    per_minute: int = Field(gt=0)
    start: AwareDatetime
    end: AwareDatetime
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class ScheduledLog(BaseModel):
    timestamp: AwareDatetime
    service: str
    status: LogStatus
    version: str
    message: str
    attributes: dict[str, JsonValue] = Field(default_factory=dict)


class Scenario(BaseModel):
    name: str
    streams: list[LogStream]
    scheduled_logs: list[ScheduledLog]


class PlaceholderValues(BaseModel):
    order_id: str
    trace_id: str
    customer_email: str
    latency_ms: int
