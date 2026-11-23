import pytest

from incident_triage.log_store.templates import message_template


@pytest.mark.parametrize(
    ("message", "template"),
    [
        (
            "PaymentClientError: 400 Bad Request - unknown field 'currency_code' "
            "(order_id=ORD-765318, customer=priya.nguyen@example.com)",
            "PaymentClientError: 400 Bad Request - unknown field 'currency_code' "
            "(order_id=<order_id>, customer=<email>)",
        ),
        ("POST /api/checkout 500 in 845ms", "POST /api/checkout 500 in <n>ms"),
        (
            "Timeout calling inventory-db after 2000ms, retry succeeded",
            "Timeout calling inventory-db after <n>ms, retry succeeded",
        ),
        ("Rolling update complete: payment-service v2.14.0", "Rolling update complete: payment-service v2.14.0"),
        ("Charge for trace 7f3a9c2e1b4d5a6f failed", "Charge for trace <id> failed"),
    ],
)
def test_template_hides_values_that_vary_per_log_but_keeps_codes_and_versions(message: str, template: str) -> None:
    assert message_template(message) == template
