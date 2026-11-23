from datetime import UTC, datetime

import pytest

from incident_triage.models.datadog import LogStatus
from mock_logs.models import LogStream, Scenario, ScheduledLog


@pytest.fixture
def order_stream() -> LogStream:
    return LogStream(
        service="checkout-service",
        status=LogStatus.INFO,
        version="3.8.1",
        messages=["Order placed"],
        per_minute=2,
        start=datetime(2026, 11, 17, 2, 0, tzinfo=UTC),
        end=datetime(2026, 11, 17, 2, 2, tzinfo=UTC),
        attributes={"http": {"status_code": 200}},
    )


@pytest.fixture
def deploy_log() -> ScheduledLog:
    return ScheduledLog(
        timestamp=datetime(2026, 11, 17, 2, 1, 0, tzinfo=UTC),
        service="payment-service",
        status=LogStatus.INFO,
        version="2.14.0",
        message="Rolling update complete: payment-service v2.14.0",
    )


@pytest.fixture
def small_scenario(order_stream: LogStream, deploy_log: ScheduledLog) -> Scenario:
    return Scenario(name="small", streams=[order_stream], scheduled_logs=[deploy_log])
