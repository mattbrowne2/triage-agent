Search past incident tickets for ones that looked like the current incident.

What it does: finds past incidents whose symptoms and confirmed root causes are semantically similar to your query, across all services, most similar first. Each match has a `similarity` score (1.0 is identical) and the `incident`: key, title, service, symptoms, when it opened, and its `resolution`. A resolution holds what engineers confirmed after the fact: the `confirmed_root_cause`, the `fix`, and `changes` (rollbacks, pull requests and config changes, with links). `resolution` is null when the incident is still open and unexplained. Weak matches are left out, so an empty `matches` list means nothing similar has happened before.

When to use it:
- After the logs have shown you what is failing, to find out whether something similar has happened before and how it was fixed.
- To check whether noise you see in the logs is a known, harmless pattern.
- To find an open incident that the current one may be part of.

When not to use it:
- Not as evidence. A past incident is precedent: rely on a past cause only after the current logs show the same thing.
- Not before you have looked at the logs. Search with what you observed, not with the alert text alone.

Inputs:
- `query` (required): a description of what you observed, in plain words. Include the error messages, the affected services and anything that changed just before it started.
- `limit` (optional, default 3, max 10).

Examples:
- Checkout failing after a deploy: {"query": "checkout-service HTTP 500, PaymentClientError 400 Bad Request unknown field 'currency_code', started right after payment-service rolling update to v2.14.0"}
- Background warnings that may be noise: {"query": "inventory-service warnings Timeout calling inventory-db after 2000ms, retry succeeded"}
