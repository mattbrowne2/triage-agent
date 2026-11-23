from collections.abc import Callable
from datetime import datetime

from incident_triage.models.alert import Alert
from incident_triage.models.datadog import Log, LogArchive, LogStatus
from mock_logs.generator import generate_archive
from mock_logs.main import DEFAULT_SEED
from mock_logs.scenarios.payment_service_bad_deploy import PAYMENT_SERVICE_BAD_DEPLOY
from monitor.error_rate_monitor import ErrorRateMonitor
from monitor.models import Check, MonitorRule
from monitor.replay import replay


def test_replay_checks_every_minute_in_log_time_and_alerts_as_errors_arrive(
    small_rule_monitor: ErrorRateMonitor,
    service_log_factory: Callable[..., Log],
    checkout_burst_factory: Callable[[int, int], list[Log]],
    at_minute: Callable[[int], datetime],
) -> None:
    archive = LogArchive(
        data=[*checkout_burst_factory(2, 3), service_log_factory("checkout-service", LogStatus.INFO, 0, 30)]
    )

    checks = list(replay(archive, small_rule_monitor))

    assert checks == [
        Check(at=at_minute(1), alerts=[]),
        Check(at=at_minute(2), alerts=[]),
        Check(
            at=at_minute(3),
            alerts=[
                Alert(
                    id="error-rate:checkout-service:2026-11-17T01:58:00Z",
                    monitor="error-rate",
                    service="checkout-service",
                    window_start=at_minute(3).replace(hour=1, minute=58),
                    window_end=at_minute(3),
                    error_count=3,
                    log_count=4,
                    threshold=0.05,
                )
            ],
        ),
    ]


def test_bad_deploy_scenario_fires_once_each_for_checkout_and_web_frontend_a_minute_after_onset(
    at_minute: Callable[[int], datetime],
) -> None:
    archive = generate_archive(PAYMENT_SERVICE_BAD_DEPLOY, seed=DEFAULT_SEED)

    alerts = [alert for check in replay(archive, ErrorRateMonitor(MonitorRule())) for alert in check.alerts]

    assert alerts == [
        Alert(
            id="error-rate:checkout-service:2026-11-17T02:05:00Z",
            monitor="error-rate",
            service="checkout-service",
            window_start=at_minute(5),
            window_end=at_minute(10),
            error_count=15,
            log_count=45,
            threshold=0.05,
        ),
        Alert(
            id="error-rate:web-frontend:2026-11-17T02:05:00Z",
            monitor="error-rate",
            service="web-frontend",
            window_start=at_minute(5),
            window_end=at_minute(10),
            error_count=15,
            log_count=55,
            threshold=0.05,
        ),
    ]
