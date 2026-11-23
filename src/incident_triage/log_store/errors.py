from collections.abc import Iterable
from datetime import datetime


class LogSearchError(Exception):
    pass


class UnknownServiceError(LogSearchError):
    def __init__(self, service: str, known_services: Iterable[str]) -> None:
        super().__init__(f"Unknown service '{service}'. Known services: {', '.join(sorted(known_services))}")


class InvalidTimeWindowError(LogSearchError):
    def __init__(self, start: datetime, end: datetime) -> None:
        super().__init__(f"Invalid time window: end {end.isoformat()} must be after start {start.isoformat()}")
