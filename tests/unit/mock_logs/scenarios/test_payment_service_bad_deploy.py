from datetime import UTC, datetime

from incident_triage.models.datadog import LogStatus
from mock_logs.generator import generate_archive
from mock_logs.scenarios.payment_service_bad_deploy import PAYMENT_SERVICE_BAD_DEPLOY


DEPLOY_COMPLETE = datetime(2026, 11, 17, 2, 8, 47, tzinfo=UTC)


def test_checkout_errors_only_start_after_payment_deploy_completes() -> None:
    archive = generate_archive(PAYMENT_SERVICE_BAD_DEPLOY, seed=42)

    first_checkout_error = next(
        log.attributes
        for log in archive.data
        if log.attributes.service == "checkout-service" and log.attributes.status == LogStatus.ERROR
    )
    assert (first_checkout_error.timestamp > DEPLOY_COMPLETE, first_checkout_error.message.split(" (")[0]) == (
        True,
        "PaymentClientError: 400 Bad Request - unknown field 'currency_code'",
    )


def test_inventory_timeouts_are_present_before_the_incident_as_background_noise() -> None:
    archive = generate_archive(PAYMENT_SERVICE_BAD_DEPLOY, seed=42)

    assert any(
        log.attributes.service == "inventory-service"
        and log.attributes.status == LogStatus.WARN
        and log.attributes.timestamp < DEPLOY_COMPLETE
        for log in archive.data
    )
