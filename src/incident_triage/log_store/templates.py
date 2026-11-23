import re

from incident_triage.pii import EMAIL_PATTERN


VARYING_VALUES = [
    (EMAIL_PATTERN, "<email>"),
    (re.compile(r"\b[A-Z]{2,}-\d+\b"), "<order_id>"),
    (re.compile(r"\b\d+ms\b"), "<n>ms"),
    (re.compile(r"\b[0-9a-f]{12,}\b"), "<id>"),
]


def message_template(message: str) -> str:
    for pattern, placeholder in VARYING_VALUES:
        message = pattern.sub(placeholder, message)
    return message
