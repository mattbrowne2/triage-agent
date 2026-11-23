from incident_triage.models.alert import Alert


def render_alert(alert: Alert) -> str:
    return (
        f"{alert.id}: monitor '{alert.monitor}' fired for {alert.service}. "
        f"In its evaluation window, {alert.window_start.isoformat()} to {alert.window_end.isoformat()}, "
        f"{alert.error_count} of {alert.log_count} logs had status error: "
        f"an error rate of {alert.error_rate:.0%} against a threshold of {alert.threshold:.0%}. "
        "The window is when the monitor measured, not when the errors started; the monitor does not determine onset."
    )
