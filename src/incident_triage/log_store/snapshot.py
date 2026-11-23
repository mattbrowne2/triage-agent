from datetime import datetime

from incident_triage.models.datadog import LogArchive


def snapshot(archive: LogArchive, as_of: datetime) -> LogArchive:
    return LogArchive(data=[log for log in archive.data if log.attributes.timestamp < as_of])
