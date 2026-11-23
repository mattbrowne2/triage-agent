Summarize every service's logs in a time window as message patterns with counts.

What it does: groups the logs of all services in the window by service, status and message template, where values that change from log to log (customer emails, order IDs, latencies, long IDs) are replaced by placeholders such as `<email>`, `<order_id>` and `<n>ms`. Each pattern has its `count`, `first_seen` and `last_seen`. Status codes, versions and field names are kept. `total_logs` is the number of logs in the window.

When to use it:
- At the start of an investigation, to see everything that is happening across all services, not only the service the alert names.
- To compare the window before the incident with the window during it: a pattern that was already present before is background noise, and a pattern that starts at the incident is a candidate cause or symptom.
- To find warnings or errors in other services that you must either connect to the incident or rule out.

When not to use it:
- Not to read individual logs, trace IDs or exact timestamps. Use query_logs for those, filtered by what the summary showed you.

Inputs:
- `start`, `end` (required): ISO 8601 timestamps with timezone, end after start.

Examples:
- Everything during the incident window: {"start": "2026-11-17T02:05:00Z", "end": "2026-11-17T02:15:00Z"}
- The baseline before it, to see what was already normal: {"start": "2026-11-17T01:45:00Z", "end": "2026-11-17T02:05:00Z"}
