from incident_triage.agent.alert_message import render_alert
from incident_triage.models.alert import Alert


def test_render_alert_states_what_the_monitor_measured_and_that_it_did_not_determine_onset(
    checkout_error_rate_alert: Alert,
) -> None:
    assert render_alert(checkout_error_rate_alert) == (
        "error-rate:checkout-service:2026-11-17T02:05:00Z: monitor 'error-rate' fired for checkout-service. "
        "In its evaluation window, 2026-11-17T02:05:00+00:00 to 2026-11-17T02:10:00+00:00, "
        "15 of 45 logs had status error: an error rate of 33% against a threshold of 5%. "
        "The window is when the monitor measured, not when the errors started; the monitor does not determine onset."
    )
