from pydantic import AwareDatetime, BaseModel, Field, computed_field


class Alert(BaseModel):
    id: str
    monitor: str
    service: str
    window_start: AwareDatetime
    window_end: AwareDatetime
    error_count: int = Field(ge=0)
    log_count: int = Field(ge=1)
    threshold: float = Field(gt=0, le=1)

    @computed_field
    @property
    def error_rate(self) -> float:
        return self.error_count / self.log_count
