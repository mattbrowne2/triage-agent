from datetime import UTC, datetime
from pathlib import Path

import pytest

from incident_triage.log_store.errors import InvalidTimeWindowError, UnknownServiceError
from incident_triage.log_store.repository import LogRepository
from incident_triage.models.datadog import Log, LogArchive, LogStatus
from incident_triage.models.log_patterns import LogPattern, LogPatternQuery, LogPatternSummary
from incident_triage.models.log_search import LogSearchMeta, LogSearchQuery, LogSearchResponse


INCIDENT_WINDOW_START = datetime(2026, 11, 17, 2, 0, tzinfo=UTC)
INCIDENT_WINDOW_END = datetime(2026, 11, 17, 2, 30, tzinfo=UTC)


def test_search_returns_logs_in_window_most_recent_first(
    log_repository: LogRepository,
    checkout_payment_error_log: Log,
    checkout_order_info_log: Log,
    payment_deploy_log: Log,
) -> None:
    response = log_repository.search(LogSearchQuery(start=INCIDENT_WINDOW_START, end=INCIDENT_WINDOW_END))

    assert response == LogSearchResponse(
        data=[checkout_payment_error_log, payment_deploy_log, checkout_order_info_log],
        meta=LogSearchMeta(total_matches=3),
    )


def test_search_filters_by_service_and_status(log_repository: LogRepository, checkout_payment_error_log: Log) -> None:
    query = LogSearchQuery(
        start=INCIDENT_WINDOW_START,
        end=INCIDENT_WINDOW_END,
        service="checkout-service",
        status=LogStatus.ERROR,
    )

    response = log_repository.search(query)

    assert response == LogSearchResponse(data=[checkout_payment_error_log], meta=LogSearchMeta(total_matches=1))


def test_search_matches_message_text_case_insensitively(log_repository: LogRepository, payment_deploy_log: Log) -> None:
    query = LogSearchQuery(start=INCIDENT_WINDOW_START, end=INCIDENT_WINDOW_END, message_contains="ROLLING UPDATE")

    response = log_repository.search(query)

    assert response == LogSearchResponse(data=[payment_deploy_log], meta=LogSearchMeta(total_matches=1))


def test_search_excludes_logs_at_window_end(log_repository: LogRepository, checkout_order_info_log: Log) -> None:
    query = LogSearchQuery(start=INCIDENT_WINDOW_START, end=datetime(2026, 11, 17, 2, 8, 47, tzinfo=UTC))

    response = log_repository.search(query)

    assert response == LogSearchResponse(data=[checkout_order_info_log], meta=LogSearchMeta(total_matches=1))


def test_search_limit_truncates_data_but_reports_total_matches(
    log_repository: LogRepository, checkout_payment_error_log: Log
) -> None:
    query = LogSearchQuery(start=INCIDENT_WINDOW_START, end=INCIDENT_WINDOW_END, limit=1)

    response = log_repository.search(query)

    assert response == LogSearchResponse(data=[checkout_payment_error_log], meta=LogSearchMeta(total_matches=3))


def test_search_for_unknown_service_raises_error_listing_known_services(log_repository: LogRepository) -> None:
    query = LogSearchQuery(start=INCIDENT_WINDOW_START, end=INCIDENT_WINDOW_END, service="payments")

    with pytest.raises(UnknownServiceError) as error:
        log_repository.search(query)

    assert str(error.value) == "Unknown service 'payments'. Known services: checkout-service, payment-service"


def test_search_with_end_before_start_raises_invalid_time_window_error(log_repository: LogRepository) -> None:
    query = LogSearchQuery(start=INCIDENT_WINDOW_END, end=INCIDENT_WINDOW_START)

    with pytest.raises(InvalidTimeWindowError) as error:
        log_repository.search(query)

    assert str(error.value) == (
        "Invalid time window: end 2026-11-17T02:00:00+00:00 must be after start 2026-11-17T02:30:00+00:00"
    )


def test_from_file_loads_archive_written_as_json(tmp_path: Path, log_archive: LogArchive) -> None:
    archive_path = tmp_path / "logs.json"
    archive_path.write_text(log_archive.model_dump_json())

    repository = LogRepository.from_file(archive_path)

    assert repository.search(LogSearchQuery(start=INCIDENT_WINDOW_START, end=INCIDENT_WINDOW_END)) == LogRepository(
        log_archive
    ).search(LogSearchQuery(start=INCIDENT_WINDOW_START, end=INCIDENT_WINDOW_END))


def test_summarize_groups_logs_in_window_into_patterns_per_service(log_repository: LogRepository) -> None:
    summary = log_repository.summarize(LogPatternQuery(start=INCIDENT_WINDOW_START, end=INCIDENT_WINDOW_END))

    assert summary == LogPatternSummary(
        total_logs=3,
        patterns=[
            LogPattern(
                service="checkout-service",
                status=LogStatus.INFO,
                template="Order placed successfully",
                count=1,
                first_seen=datetime(2026, 11, 17, 2, 1, 30, tzinfo=UTC),
                last_seen=datetime(2026, 11, 17, 2, 1, 30, tzinfo=UTC),
            ),
            LogPattern(
                service="checkout-service",
                status=LogStatus.ERROR,
                template="PaymentClientError: 400 Bad Request - unknown field 'currency_code'",
                count=1,
                first_seen=datetime(2026, 11, 17, 2, 10, 4, tzinfo=UTC),
                last_seen=datetime(2026, 11, 17, 2, 10, 4, tzinfo=UTC),
            ),
            LogPattern(
                service="payment-service",
                status=LogStatus.INFO,
                template="Rolling update complete: payment-service v2.14.0",
                count=1,
                first_seen=datetime(2026, 11, 17, 2, 8, 47, tzinfo=UTC),
                last_seen=datetime(2026, 11, 17, 2, 8, 47, tzinfo=UTC),
            ),
        ],
    )


def test_summarize_rejects_a_reversed_time_window(log_repository: LogRepository) -> None:
    with pytest.raises(InvalidTimeWindowError):
        log_repository.summarize(LogPatternQuery(start=INCIDENT_WINDOW_END, end=INCIDENT_WINDOW_START))
