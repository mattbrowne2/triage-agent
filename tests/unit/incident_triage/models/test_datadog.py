from datetime import UTC, datetime

from incident_triage.models.datadog import Log, LogArchive, LogAttributes, LogStatus


def test_log_archive_parses_datadog_search_api_payload() -> None:
    payload = """
    {
      "data": [
        {
          "id": "AAAAAWgN8Xwgr1vKDQAAAABBV2dOOFh3ZzZobm1mWXJFYTR0OA",
          "type": "log",
          "attributes": {
            "timestamp": "2026-11-17T02:10:04Z",
            "status": "error",
            "service": "checkout-service",
            "host": "checkout-service-7d9f-x2k4p",
            "message": "PaymentClientError: 400 Bad Request",
            "tags": ["env:prod", "service:checkout-service"],
            "attributes": {"trace_id": "7f3a9c2e", "http": {"status_code": 500}}
          }
        }
      ]
    }
    """

    archive = LogArchive.model_validate_json(payload)

    assert archive == LogArchive(
        data=[
            Log(
                id="AAAAAWgN8Xwgr1vKDQAAAABBV2dOOFh3ZzZobm1mWXJFYTR0OA",
                attributes=LogAttributes(
                    timestamp=datetime(2026, 11, 17, 2, 10, 4, tzinfo=UTC),
                    status=LogStatus.ERROR,
                    service="checkout-service",
                    host="checkout-service-7d9f-x2k4p",
                    message="PaymentClientError: 400 Bad Request",
                    tags=["env:prod", "service:checkout-service"],
                    attributes={"trace_id": "7f3a9c2e", "http": {"status_code": 500}},
                ),
            )
        ]
    )
