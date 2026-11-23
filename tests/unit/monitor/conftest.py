from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from incident_triage.models.datadog import Log, LogAttributes, LogStatus
from monitor.error_rate_monitor import ErrorRateMonitor
from monitor.models import MonitorRule


@pytest.fixture
def service_log_factory() -> Callable[..., Log]:
    def build(service: str, status: LogStatus, minute: int, second: int = 0) -> Log:
        return Log(
            id=f"{service}-{minute:02d}{second:02d}-{status}",
            attributes=LogAttributes(
                timestamp=datetime(2026, 11, 17, 2, minute, second, tzinfo=UTC),
                status=status,
                service=service,
                host=f"{service}-pod-1",
                message=f"{status} log",
                tags=[f"service:{service}"],
                attributes={},
            ),
        )

    return build


@pytest.fixture
def small_rule() -> MonitorRule:
    return MonitorRule(window_minutes=5, max_error_rate=0.05, min_errors=3, recovery_checks=2)


@pytest.fixture
def small_rule_monitor(small_rule: MonitorRule) -> ErrorRateMonitor:
    return ErrorRateMonitor(small_rule)


@pytest.fixture
def checkout_burst_factory(service_log_factory: Callable[..., Log]) -> Callable[[int, int], list[Log]]:
    def build(minute: int, errors: int) -> list[Log]:
        return [service_log_factory("checkout-service", LogStatus.ERROR, minute, second) for second in range(errors)]

    return build


@pytest.fixture
def at_minute() -> Callable[[int], datetime]:
    def build(minute: int) -> datetime:
        return datetime(2026, 11, 17, 2, minute, tzinfo=UTC)

    return build
