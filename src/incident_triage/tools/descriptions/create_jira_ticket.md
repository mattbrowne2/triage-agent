File a Jira ticket for the on-call team about this incident.

What it does: creates one ticket in the OPS project and returns Jira's create-issue response: the ticket `id`, its `key` (such as OPS-1) and its `self` link. Each alert can have only one ticket: if you file again for the same alert, you get the existing ticket back and nothing new is created. A ticket that contains customer email addresses is rejected with an error that says so; remove the personal data and file again.

When to use it:
- Once, after your investigation, when the logs confirm an incident that needs on-call attention. File it before you submit your report, and put its key in the report's `ticket_key`.

When not to use it:
- When the logs show no incident, or the alert is not supported by the logs and nothing else is wrong. Say so in your report instead.
- Not as a way to take or claim any other action. The ticket recommends actions; it does not perform them.

Inputs:
- `summary` (required): one line, 10 to 120 characters, naming the symptom and the likely cause.
- `description` (required): the alert, impact, root cause with confidence, key evidence (timestamps, versions, trace IDs), what you ruled out, related past incidents with their links, and recommended next steps. No customer personal data.
- `priority` (required): Highest when customers are failing now, High for degraded service, Medium or Low otherwise.
- `service` (required): the service whose owners need to act, usually the one with the root cause.

Example:
{"summary": "Checkout failing: payment-service v2.14.0 rejects currency_code", "description": "Since 02:09 UTC ...", "priority": "Highest", "service": "payment-service"}
