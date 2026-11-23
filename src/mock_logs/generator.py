from base64 import urlsafe_b64encode
from collections.abc import Iterator
from datetime import datetime, timedelta
from random import Random

from pydantic import JsonValue

from incident_triage.models.datadog import Log, LogArchive, LogAttributes, LogStatus
from mock_logs.models import LogStream, Scenario, ScheduledLog
from mock_logs.placeholders import random_placeholder_values


PODS_PER_SERVICE = 3


def generate_archive(scenario: Scenario, seed: int) -> LogArchive:
    rng = Random(seed)
    logs = [
        *(log for stream in scenario.streams for log in _stream_logs(stream, rng)),
        *(_scheduled_log(scheduled, rng) for scheduled in scenario.scheduled_logs),
    ]
    return LogArchive(data=sorted(logs, key=lambda log: log.attributes.timestamp))


def _stream_logs(stream: LogStream, rng: Random) -> Iterator[Log]:
    minutes = int((stream.end - stream.start).total_seconds() // 60)
    for minute in range(minutes):
        for _ in range(stream.per_minute):
            offset = timedelta(minutes=minute, milliseconds=rng.randrange(60_000))
            placeholders = random_placeholder_values(rng)
            yield _log(
                rng=rng,
                timestamp=stream.start + offset,
                service=stream.service,
                status=stream.status,
                version=stream.version,
                message=rng.choice(stream.messages).format(**placeholders.model_dump()),
                attributes={"trace_id": placeholders.trace_id, **stream.attributes},
            )


def _scheduled_log(scheduled: ScheduledLog, rng: Random) -> Log:
    return _log(
        rng=rng,
        timestamp=scheduled.timestamp,
        service=scheduled.service,
        status=scheduled.status,
        version=scheduled.version,
        message=scheduled.message,
        attributes={"trace_id": random_placeholder_values(rng).trace_id, **scheduled.attributes},
    )


def _log(
    rng: Random,
    timestamp: datetime,
    service: str,
    status: LogStatus,
    version: str,
    message: str,
    attributes: dict[str, JsonValue],
) -> Log:
    return Log(
        id=f"AAAAA{urlsafe_b64encode(rng.randbytes(24)).decode()}",
        attributes=LogAttributes(
            timestamp=timestamp,
            status=status,
            service=service,
            host=f"{service}-pod-{rng.randint(1, PODS_PER_SERVICE)}",
            message=message,
            tags=["env:prod", f"service:{service}", f"version:{version}"],
            attributes=attributes,
        ),
    )
