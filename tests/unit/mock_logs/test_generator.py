import re
from datetime import UTC, datetime

from incident_triage.models.datadog import LogStatus
from mock_logs.generator import generate_archive
from mock_logs.models import LogStream, Scenario, ScheduledLog


def test_same_seed_generates_identical_archive(small_scenario: Scenario) -> None:
    assert generate_archive(small_scenario, seed=7) == generate_archive(small_scenario, seed=7)


def test_different_seeds_generate_different_archives(small_scenario: Scenario) -> None:
    assert generate_archive(small_scenario, seed=7) != generate_archive(small_scenario, seed=8)


def test_stream_emits_its_rate_every_minute_inside_its_window(order_stream: LogStream) -> None:
    archive = generate_archive(Scenario(name="orders", streams=[order_stream], scheduled_logs=[]), seed=1)

    assert [
        (log.attributes.service, log.attributes.status, log.attributes.message, log.attributes.tags)
        for log in archive.data
    ] == [
        ("checkout-service", LogStatus.INFO, "Order placed", ["env:prod", "service:checkout-service", "version:3.8.1"])
    ] * 4
    assert [log.attributes.timestamp.minute for log in archive.data] == [0, 0, 1, 1]


def test_scheduled_log_is_emitted_at_its_exact_timestamp(deploy_log: ScheduledLog) -> None:
    archive = generate_archive(Scenario(name="deploy", streams=[], scheduled_logs=[deploy_log]), seed=1)

    log = archive.data[0].attributes
    assert (log.timestamp, log.service, log.status, log.message, log.tags) == (
        datetime(2026, 11, 17, 2, 1, 0, tzinfo=UTC),
        "payment-service",
        LogStatus.INFO,
        "Rolling update complete: payment-service v2.14.0",
        ["env:prod", "service:payment-service", "version:2.14.0"],
    )


def test_archive_is_sorted_oldest_first(small_scenario: Scenario) -> None:
    archive = generate_archive(small_scenario, seed=3)

    timestamps = [log.attributes.timestamp for log in archive.data]
    assert timestamps == sorted(timestamps)


def test_message_placeholders_are_filled_with_realistic_values(order_stream: LogStream) -> None:
    stream = order_stream.model_copy(update={"messages": ["Order {order_id} placed for {customer_email}"]})

    archive = generate_archive(Scenario(name="orders", streams=[stream], scheduled_logs=[]), seed=1)

    assert all(
        re.fullmatch(r"Order ORD-\d{6} placed for [a-z]+\.[a-z]+@example\.com", log.attributes.message)
        for log in archive.data
    )


def test_every_log_gets_a_trace_id_alongside_stream_attributes(order_stream: LogStream) -> None:
    archive = generate_archive(Scenario(name="orders", streams=[order_stream], scheduled_logs=[]), seed=1)

    attributes = archive.data[0].attributes.attributes
    assert (sorted(attributes), attributes["http"]) == (["http", "trace_id"], {"status_code": 200})
