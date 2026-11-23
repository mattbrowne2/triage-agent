from collections.abc import Iterator
from datetime import timedelta

from incident_triage.models.datadog import LogArchive
from monitor.error_rate_monitor import ErrorRateMonitor
from monitor.models import Check


CHECK_INTERVAL = timedelta(minutes=1)


def replay(archive: LogArchive, monitor: ErrorRateMonitor) -> Iterator[Check]:
    logs = sorted(archive.data, key=lambda log: log.attributes.timestamp)
    check_at = logs[0].attributes.timestamp.replace(second=0, microsecond=0) + CHECK_INTERVAL
    for log in logs:
        while log.attributes.timestamp >= check_at:
            yield Check(at=check_at, alerts=monitor.evaluate(check_at))
            check_at += CHECK_INTERVAL
        monitor.observe(log)
    yield Check(at=check_at, alerts=monitor.evaluate(check_at))
