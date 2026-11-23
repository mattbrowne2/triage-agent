from collections import defaultdict
from pathlib import Path
from typing import Self

from incident_triage.log_store.errors import InvalidTimeWindowError, UnknownServiceError
from incident_triage.log_store.filters import matches
from incident_triage.log_store.templates import message_template
from incident_triage.models.datadog import Log, LogArchive, LogStatus
from incident_triage.models.log_patterns import LogPattern, LogPatternQuery, LogPatternSummary
from incident_triage.models.log_search import LogSearchMeta, LogSearchQuery, LogSearchResponse


class LogRepository:
    def __init__(self, archive: LogArchive) -> None:
        self._logs = sorted(archive.data, key=lambda log: log.attributes.timestamp, reverse=True)
        self._services = frozenset(log.attributes.service for log in archive.data)

    @classmethod
    def from_file(cls, path: Path) -> Self:
        return cls(LogArchive.model_validate_json(path.read_text()))

    def search(self, query: LogSearchQuery) -> LogSearchResponse:
        if query.end <= query.start:
            raise InvalidTimeWindowError(query.start, query.end)
        if query.service is not None and query.service not in self._services:
            raise UnknownServiceError(query.service, self._services)
        matching_logs = [log for log in self._logs if matches(log, query)]
        return LogSearchResponse(
            data=matching_logs[: query.limit], meta=LogSearchMeta(total_matches=len(matching_logs))
        )

    def summarize(self, query: LogPatternQuery) -> LogPatternSummary:
        if query.end <= query.start:
            raise InvalidTimeWindowError(query.start, query.end)
        groups: defaultdict[tuple[str, LogStatus, str], list[Log]] = defaultdict(list)
        in_window = [log for log in self._logs if query.start <= log.attributes.timestamp < query.end]
        for log in in_window:
            groups[(log.attributes.service, log.attributes.status, message_template(log.attributes.message))].append(
                log
            )
        patterns = [
            LogPattern(
                service=service,
                status=status,
                template=template,
                count=len(logs),
                first_seen=min(log.attributes.timestamp for log in logs),
                last_seen=max(log.attributes.timestamp for log in logs),
            )
            for (service, status, template), logs in groups.items()
        ]
        return LogPatternSummary(
            total_logs=len(in_window),
            patterns=sorted(patterns, key=lambda pattern: (pattern.service, -pattern.count, pattern.template)),
        )
