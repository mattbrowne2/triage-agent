from collections.abc import Callable
from datetime import datetime

from incident_triage.models.alert import Alert
from incident_triage.models.datadog import Log, LogStatus
from monitor.error_rate_monitor import ErrorRateMonitor


def test_fires_once_when_error_rate_and_error_count_cross_the_rule(
    small_rule_monitor: ErrorRateMonitor,
    service_log_factory: Callable[..., Log],
    checkout_burst_factory: Callable[[int, int], list[Log]],
    at_minute: Callable[[int], datetime],
) -> None:
    for log in [service_log_factory("checkout-service", LogStatus.INFO, 6), *checkout_burst_factory(9, 3)]:
        small_rule_monitor.observe(log)

    alerts = small_rule_monitor.evaluate(at_minute(10))

    assert alerts == [
        Alert(
            id="error-rate:checkout-service:2026-11-17T02:05:00Z",
            monitor="error-rate",
            service="checkout-service",
            window_start=at_minute(5),
            window_end=at_minute(10),
            error_count=3,
            log_count=4,
            threshold=0.05,
        )
    ]


def test_stays_quiet_when_errors_are_below_the_minimum_count_however_high_the_rate(
    small_rule_monitor: ErrorRateMonitor,
    checkout_burst_factory: Callable[[int, int], list[Log]],
    at_minute: Callable[[int], datetime],
) -> None:
    for log in checkout_burst_factory(9, 2):
        small_rule_monitor.observe(log)

    assert small_rule_monitor.evaluate(at_minute(10)) == []


def test_stays_quiet_when_error_rate_is_at_or_below_the_threshold(
    small_rule_monitor: ErrorRateMonitor,
    service_log_factory: Callable[..., Log],
    checkout_burst_factory: Callable[[int, int], list[Log]],
    at_minute: Callable[[int], datetime],
) -> None:
    healthy_logs = [service_log_factory("checkout-service", LogStatus.INFO, 8, second) for second in range(57)]
    for log in [*healthy_logs, *checkout_burst_factory(9, 3)]:
        small_rule_monitor.observe(log)

    assert small_rule_monitor.evaluate(at_minute(10)) == []


def test_does_not_fire_again_while_the_service_keeps_breaching(
    small_rule_monitor: ErrorRateMonitor,
    checkout_burst_factory: Callable[[int, int], list[Log]],
    at_minute: Callable[[int], datetime],
) -> None:
    for log in checkout_burst_factory(9, 3):
        small_rule_monitor.observe(log)
    small_rule_monitor.evaluate(at_minute(10))
    for log in checkout_burst_factory(10, 3):
        small_rule_monitor.observe(log)

    assert small_rule_monitor.evaluate(at_minute(11)) == []


def test_fires_again_only_after_recovering_for_the_required_number_of_checks(
    small_rule_monitor: ErrorRateMonitor,
    checkout_burst_factory: Callable[[int, int], list[Log]],
    at_minute: Callable[[int], datetime],
) -> None:
    for log in checkout_burst_factory(0, 3):
        small_rule_monitor.observe(log)
    small_rule_monitor.evaluate(at_minute(1))
    quiet_checks = [small_rule_monitor.evaluate(at_minute(minute)) for minute in (6, 7)]
    for log in checkout_burst_factory(7, 3):
        small_rule_monitor.observe(log)

    second_incident = small_rule_monitor.evaluate(at_minute(8))

    assert (quiet_checks, [alert.id for alert in second_incident]) == (
        [[], []],
        ["error-rate:checkout-service:2026-11-17T02:03:00Z"],
    )


def test_does_not_fire_again_when_errors_return_before_recovery_completes(
    small_rule_monitor: ErrorRateMonitor,
    checkout_burst_factory: Callable[[int, int], list[Log]],
    at_minute: Callable[[int], datetime],
) -> None:
    for log in checkout_burst_factory(0, 3):
        small_rule_monitor.observe(log)
    small_rule_monitor.evaluate(at_minute(1))
    small_rule_monitor.evaluate(at_minute(6))
    for log in checkout_burst_factory(6, 3):
        small_rule_monitor.observe(log)

    assert small_rule_monitor.evaluate(at_minute(7)) == []
