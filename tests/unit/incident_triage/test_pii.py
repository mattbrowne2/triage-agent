from incident_triage.pii import find_emails


def test_find_emails_returns_every_email_address_in_the_text() -> None:
    assert find_emails("customer=priya.nguyen@example.com and sam.smith+test@shop.example.co.uk") == [
        "priya.nguyen@example.com",
        "sam.smith+test@shop.example.co.uk",
    ]


def test_find_emails_ignores_text_without_addresses() -> None:
    assert find_emails("PaymentClientError: 400 Bad Request - unknown field 'currency_code'") == []
