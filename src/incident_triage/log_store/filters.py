from incident_triage.models.datadog import Log
from incident_triage.models.log_search import LogSearchQuery


def matches(log: Log, query: LogSearchQuery) -> bool:
    attributes = log.attributes
    return (
        query.start <= attributes.timestamp < query.end
        and query.service in (None, attributes.service)
        and query.status in (None, attributes.status)
        and (query.message_contains is None or query.message_contains.lower() in attributes.message.lower())
    )
