import time
from argparse import ArgumentParser
from pathlib import Path

from incident_triage.models.datadog import LogArchive
from monitor.client import build_client, send_alert
from monitor.error_rate_monitor import ErrorRateMonitor
from monitor.models import MonitorRule
from monitor.replay import replay


DEFAULT_LOGS_PATH = Path("data/datadog_logs/payment_service_bad_deploy.json")
DEFAULT_API_URL = "http://localhost:8000"


def main() -> None:
    parser = ArgumentParser(description="Replay a log archive through the error-rate monitor and send its alerts")
    parser.add_argument("--logs", type=Path, default=DEFAULT_LOGS_PATH)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--seconds-per-check", type=float, default=1.0, help="Real seconds per simulated minute")
    arguments = parser.parse_args()

    archive = LogArchive.model_validate_json(arguments.logs.read_text())
    monitor = ErrorRateMonitor(MonitorRule())

    with build_client(arguments.api_url) as client:
        for check in replay(archive, monitor):
            for alert in check.alerts:
                print(send_alert(client, alert).model_dump_json())
            time.sleep(arguments.seconds_per_check)


if __name__ == "__main__":
    main()
