from datetime import UTC, datetime

from incident_triage.log_store.snapshot import snapshot
from incident_triage.models.datadog import Log, LogArchive


def test_snapshot_keeps_only_logs_written_before_the_investigation_time(
    log_archive: LogArchive, checkout_order_info_log: Log, payment_deploy_log: Log
) -> None:
    assert snapshot(log_archive, as_of=datetime(2026, 11, 17, 2, 10, tzinfo=UTC)) == LogArchive(
        data=[checkout_order_info_log, payment_deploy_log]
    )
