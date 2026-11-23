from collections import Counter
from datetime import datetime, timedelta

from incident_triage.models.datadog import Log, LogStatus
from monitor.models import WindowCount


ERROR_STATUSES = frozenset({LogStatus.ERROR, LogStatus.CRITICAL, LogStatus.ALERT, LogStatus.EMERGENCY})

type Bucket = tuple[str, datetime]


class ErrorCountWindow:
    def __init__(self, length: timedelta) -> None:
        self._length = length
        self._services: set[str] = set()
        self._logs: Counter[Bucket] = Counter()
        self._errors: Counter[Bucket] = Counter()

    def add(self, log: Log) -> None:
        bucket = (log.attributes.service, log.attributes.timestamp.replace(second=0, microsecond=0))
        self._services.add(log.attributes.service)
        self._logs[bucket] += 1
        if log.attributes.status in ERROR_STATUSES:
            self._errors[bucket] += 1

    def counts(self, now: datetime) -> list[WindowCount]:
        start = now - self._length
        for bucket in [bucket for bucket in self._logs if bucket[1] < start]:
            del self._logs[bucket]
            del self._errors[bucket]
        return [
            WindowCount(
                service=service,
                start=start,
                end=now,
                error_count=_total(self._errors, service, now),
                log_count=_total(self._logs, service, now),
            )
            for service in sorted(self._services)
        ]


def _total(counter: Counter[Bucket], service: str, now: datetime) -> int:
    return sum(
        count for (bucket_service, minute), count in counter.items() if bucket_service == service and minute < now
    )
