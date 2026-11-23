from enum import StrEnum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, JsonValue


class LogStatus(StrEnum):
    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARN = "warn"
    ERROR = "error"
    CRITICAL = "critical"
    ALERT = "alert"
    EMERGENCY = "emerg"


class LogAttributes(BaseModel):
    timestamp: AwareDatetime
    status: LogStatus
    service: str
    host: str
    message: str
    tags: list[str]
    attributes: dict[str, JsonValue]


class Log(BaseModel):
    id: str
    type: Literal["log"] = "log"
    attributes: LogAttributes


class LogArchive(BaseModel):
    data: list[Log]
