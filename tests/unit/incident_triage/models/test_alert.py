import json

import pytest
from pydantic import ValidationError

from incident_triage.models.alert import Alert


def test_alert_error_rate_is_errors_over_logs_in_window(checkout_error_rate_alert: Alert) -> None:
    assert checkout_error_rate_alert.error_rate == pytest.approx(1 / 3)


def test_alert_json_includes_error_rate_and_round_trips(checkout_error_rate_alert: Alert) -> None:
    payload = checkout_error_rate_alert.model_dump_json()

    assert (json.loads(payload)["error_rate"], Alert.model_validate_json(payload)) == (
        pytest.approx(1 / 3),
        checkout_error_rate_alert,
    )


def test_alert_rejects_window_without_logs(checkout_error_rate_alert: Alert) -> None:
    with pytest.raises(ValidationError, match="log_count"):
        Alert.model_validate(checkout_error_rate_alert.model_dump() | {"log_count": 0})
