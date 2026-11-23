from datetime import datetime, timedelta

from incident_triage.models.alert import Alert
from incident_triage.models.datadog import Log
from monitor.models import MonitorRule, WindowCount
from monitor.window import ErrorCountWindow


class ErrorRateMonitor:
    def __init__(self, rule: MonitorRule) -> None:
        self._rule = rule
        self._window = ErrorCountWindow(timedelta(minutes=rule.window_minutes))
        self._healthy_checks_while_alerting: dict[str, int] = {}

    def observe(self, log: Log) -> None:
        self._window.add(log)

    def evaluate(self, now: datetime) -> list[Alert]:
        alerts = []
        for count in self._window.counts(now):
            if self._transition(count):
                alerts.append(self._alert(count))
        return alerts

    def _transition(self, count: WindowCount) -> bool:
        alerting = count.service in self._healthy_checks_while_alerting
        match alerting, self._breaches(count):
            case False, True:
                self._healthy_checks_while_alerting[count.service] = 0
                return True
            case True, True:
                self._healthy_checks_while_alerting[count.service] = 0
            case True, False:
                self._healthy_checks_while_alerting[count.service] += 1
                if self._healthy_checks_while_alerting[count.service] >= self._rule.recovery_checks:
                    del self._healthy_checks_while_alerting[count.service]
        return False

    def _breaches(self, count: WindowCount) -> bool:
        return (
            count.error_count >= self._rule.min_errors
            and count.error_count / count.log_count > self._rule.max_error_rate
        )

    def _alert(self, count: WindowCount) -> Alert:
        return Alert(
            id=f"{self._rule.name}:{count.service}:{count.start:%Y-%m-%dT%H:%M:%SZ}",
            monitor=self._rule.name,
            service=count.service,
            window_start=count.start,
            window_end=count.end,
            error_count=count.error_count,
            log_count=count.log_count,
            threshold=self._rule.max_error_rate,
        )
