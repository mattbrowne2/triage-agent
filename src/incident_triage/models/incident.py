from enum import StrEnum, auto

from pydantic import AwareDatetime, BaseModel


class ChangeKind(StrEnum):
    ROLLBACK = auto()
    PULL_REQUEST = auto()
    CONFIG_CHANGE = auto()


class ChangeLink(BaseModel):
    kind: ChangeKind
    ref: str
    url: str


class Resolution(BaseModel):
    confirmed_root_cause: str
    fix: str
    changes: list[ChangeLink]
    resolved_at: AwareDatetime
    agent_was_right: bool | None


class PastIncident(BaseModel):
    key: str
    title: str
    service: str
    symptoms: str
    opened_at: AwareDatetime
    resolution: Resolution | None


class IncidentArchive(BaseModel):
    incidents: list[PastIncident]
