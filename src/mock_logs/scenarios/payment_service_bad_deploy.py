from datetime import UTC, datetime

from incident_triage.models.datadog import LogStatus
from mock_logs.models import LogStream, Scenario, ScheduledLog


WINDOW_START = datetime(2026, 11, 17, 1, 45, tzinfo=UTC)
WINDOW_END = datetime(2026, 11, 17, 2, 30, tzinfo=UTC)
PAYMENT_VERSION_SWITCH = datetime(2026, 11, 17, 2, 9, tzinfo=UTC)
INCIDENT_START = datetime(2026, 11, 17, 2, 9, tzinfo=UTC)

BACKGROUND_STREAMS = [
    LogStream(
        service="web-frontend",
        status=LogStatus.INFO,
        version="5.2.0",
        messages=[
            "GET /api/products 200 in {latency_ms}ms",
            "GET /api/cart 200 in {latency_ms}ms",
            "POST /api/checkout 200 in {latency_ms}ms",
        ],
        per_minute=8,
        start=WINDOW_START,
        end=WINDOW_END,
        attributes={"http": {"status_code": 200}},
    ),
    LogStream(
        service="checkout-service",
        status=LogStatus.INFO,
        version="3.8.1",
        messages=["Order {order_id} placed for {customer_email}", "Cart validated for order {order_id}"],
        per_minute=6,
        start=WINDOW_START,
        end=WINDOW_END,
    ),
    LogStream(
        service="payment-service",
        status=LogStatus.INFO,
        version="2.13.2",
        messages=["Charge authorized for order {order_id} in {latency_ms}ms"],
        per_minute=6,
        start=WINDOW_START,
        end=PAYMENT_VERSION_SWITCH,
    ),
    LogStream(
        service="payment-service",
        status=LogStatus.INFO,
        version="2.14.0",
        messages=["Charge authorized for order {order_id} in {latency_ms}ms"],
        per_minute=2,
        start=PAYMENT_VERSION_SWITCH,
        end=WINDOW_END,
    ),
    LogStream(
        service="inventory-service",
        status=LogStatus.INFO,
        version="1.21.4",
        messages=["Reserved stock for order {order_id}"],
        per_minute=4,
        start=WINDOW_START,
        end=WINDOW_END,
    ),
    LogStream(
        service="inventory-service",
        status=LogStatus.WARN,
        version="1.21.4",
        messages=["Timeout calling inventory-db after 2000ms, retry succeeded"],
        per_minute=1,
        start=WINDOW_START,
        end=WINDOW_END,
    ),
    LogStream(
        service="notification-service",
        status=LogStatus.INFO,
        version="0.9.7",
        messages=["Order confirmation email queued for {customer_email}"],
        per_minute=2,
        start=WINDOW_START,
        end=WINDOW_END,
    ),
]

INCIDENT_STREAMS = [
    LogStream(
        service="checkout-service",
        status=LogStatus.ERROR,
        version="3.8.1",
        messages=[
            "PaymentClientError: 400 Bad Request - unknown field 'currency_code' "
            "(order_id={order_id}, customer={customer_email})"
        ],
        per_minute=15,
        start=INCIDENT_START,
        end=WINDOW_END,
        attributes={"http": {"status_code": 500}, "error": {"kind": "PaymentClientError"}},
    ),
    LogStream(
        service="payment-service",
        status=LogStatus.WARN,
        version="2.14.0",
        messages=["Rejected charge request: unknown field 'currency_code' in request body"],
        per_minute=15,
        start=INCIDENT_START,
        end=WINDOW_END,
        attributes={"http": {"status_code": 400}},
    ),
    LogStream(
        service="web-frontend",
        status=LogStatus.ERROR,
        version="5.2.0",
        messages=["POST /api/checkout 500 in {latency_ms}ms"],
        per_minute=15,
        start=INCIDENT_START,
        end=WINDOW_END,
        attributes={"http": {"status_code": 500}},
    ),
]

DEPLOY_LOGS = [
    ScheduledLog(
        timestamp=datetime(2026, 11, 17, 2, 5, 12, tzinfo=UTC),
        service="payment-service",
        status=LogStatus.INFO,
        version="2.14.0",
        message="Rolling update started: payment-service v2.13.2 -> v2.14.0",
        attributes={"deploy": {"commit": "7c411bf", "triggered_by": "ci-pipeline"}},
    ),
    ScheduledLog(
        timestamp=datetime(2026, 11, 17, 2, 6, 30, tzinfo=UTC),
        service="payment-service",
        status=LogStatus.INFO,
        version="2.14.0",
        message="Pod payment-service-pod-1 ready on v2.14.0",
    ),
    ScheduledLog(
        timestamp=datetime(2026, 11, 17, 2, 7, 41, tzinfo=UTC),
        service="payment-service",
        status=LogStatus.INFO,
        version="2.14.0",
        message="Pod payment-service-pod-2 ready on v2.14.0",
    ),
    ScheduledLog(
        timestamp=datetime(2026, 11, 17, 2, 8, 47, tzinfo=UTC),
        service="payment-service",
        status=LogStatus.INFO,
        version="2.14.0",
        message="Rolling update complete: payment-service v2.14.0",
        attributes={"deploy": {"commit": "7c411bf", "triggered_by": "ci-pipeline"}},
    ),
]

PAYMENT_SERVICE_BAD_DEPLOY = Scenario(
    name="payment_service_bad_deploy",
    streams=[*BACKGROUND_STREAMS, *INCIDENT_STREAMS],
    scheduled_logs=DEPLOY_LOGS,
)
