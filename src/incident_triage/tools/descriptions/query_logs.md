Search production logs exported from Datadog.

What it does: returns logs inside a time window, filtered by service, status and message text, most recent first. The response is Datadog Logs Search API shaped: `data` holds the logs (each with `attributes.timestamp`, `status`, `service`, `host`, `message`, `tags` and nested `attributes` such as `trace_id`), and `meta.total_matches` holds how many logs matched before `limit` was applied.

When to use it:
- To find the errors behind an alert and what they say.
- To check what changed around the time an incident started, such as deploys or config changes (search status info with message text like "deploy" or "rolling update").
- To compare a service's behaviour before and after an incident started.

When not to use it:
- Do not page through every log. Narrow the window, service, status or message text instead, and use `meta.total_matches` for volume.
- Do not guess service names. If a service is unknown, the error lists the services that exist.

Inputs:
- `start`, `end` (required): ISO 8601 timestamps with timezone, end after start. Example: "2026-11-17T02:00:00Z".
- `service` (optional): exact service name.
- `status` (optional): one of debug, info, notice, warn, error, critical, alert, emerg.
- `message_contains` (optional): case-insensitive substring of the log message.
- `limit` (optional, default 25, max 100).

Examples:
- Errors from checkout during the alert: {"start": "2026-11-17T02:05:00Z", "end": "2026-11-17T02:20:00Z", "service": "checkout-service", "status": "error"}
- Deploys across all services in the hour before: {"start": "2026-11-17T01:15:00Z", "end": "2026-11-17T02:15:00Z", "message_contains": "rolling update"}
