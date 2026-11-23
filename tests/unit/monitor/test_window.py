from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from incident_triage.models.datadog import Log, LogStatus
from monitor.models import WindowCount
from monitor.window import ErrorCountWindow


WINDOW = timedelta(minutes=5)


def test_counts_errors_and_logs_per_service_within_the_window(service_log_factory: Callable[..., Log]) -> None:
    window = ErrorCountWindow(WINDOW)
    for log in [
        service_log_factory("checkout-service", LogStatus.INFO, 6),
        service_log_factory("checkout-service", LogStatus.ERROR, 9, 1),
        service_log_factory("checkout-service", LogStatus.CRITICAL, 9, 2),
        service_log_factory("checkout-service", LogStatus.WARN, 9, 3),
        service_log_factory("inventory-service", LogStatus.WARN, 7),
    ]:
        window.add(log)

    counts = window.counts(datetime(2026, 11, 17, 2, 10, tzinfo=UTC))

    assert counts == [
        WindowCount(
            service="checkout-service",
            start=datetime(2026, 11, 17, 2, 5, tzinfo=UTC),
            end=datetime(2026, 11, 17, 2, 10, tzinfo=UTC),
            error_count=2,
            log_count=4,
        ),
        WindowCount(
            service="inventory-service",
            start=datetime(2026, 11, 17, 2, 5, tzinfo=UTC),
            end=datetime(2026, 11, 17, 2, 10, tzinfo=UTC),
            error_count=0,
            log_count=1,
        ),
    ]


def test_drops_logs_older_than_the_window_but_keeps_reporting_the_service(
    service_log_factory: Callable[..., Log],
) -> None:
    window = ErrorCountWindow(WINDOW)
    window.add(service_log_factory("checkout-service", LogStatus.ERROR, 1))
    window.counts(datetime(2026, 11, 17, 2, 2, tzinfo=UTC))

    counts = window.counts(datetime(2026, 11, 17, 2, 10, tzinfo=UTC))

    assert counts == [
        WindowCount(
            service="checkout-service",
            start=datetime(2026, 11, 17, 2, 5, tzinfo=UTC),
            end=datetime(2026, 11, 17, 2, 10, tzinfo=UTC),
            error_count=0,
            log_count=0,
        )
    ]
