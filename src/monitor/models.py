from pydantic import AwareDatetime, BaseModel, Field

from incident_triage.models.alert import Alert


class MonitorRule(BaseModel):
    name: str = "error-rate"
    window_minutes: int = Field(default=5, ge=1)
    max_error_rate: float = Field(default=0.05, gt=0, le=1)
    min_errors: int = Field(default=10, ge=1)
    recovery_checks: int = Field(default=3, ge=1)


class WindowCount(BaseModel):
    service: str
    start: AwareDatetime
    end: AwareDatetime
    error_count: int
    log_count: int


class Check(BaseModel):
    at: AwareDatetime
    alerts: list[Alert]


class Delivery(BaseModel):
    alert_id: str
    delivered: bool
    detail: str
