from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field

from incident_triage.models.datadog import Log, LogStatus


class LogSearchQuery(BaseModel):
    start: AwareDatetime = Field(description="Inclusive start of the time window, ISO 8601 with timezone")
    end: AwareDatetime = Field(description="Exclusive end of the time window, ISO 8601 with timezone")
    service: str | None = Field(default=None, description="Exact service name, e.g. checkout-service")
    status: LogStatus | None = Field(default=None, description="Log status to match")
    message_contains: str | None = Field(default=None, description="Case-insensitive text the message must contain")
    limit: int = Field(default=25, ge=1, le=100, description="Maximum logs returned, most recent first")


class LogSearchMeta(BaseModel):
    status: Literal["done"] = "done"
    total_matches: int


class LogSearchResponse(BaseModel):
    data: list[Log]
    meta: LogSearchMeta
