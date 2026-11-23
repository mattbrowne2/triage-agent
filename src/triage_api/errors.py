class TriageNotFoundError(Exception):
    def __init__(self, alert_id: str) -> None:
        super().__init__(f"No triage for alert '{alert_id}'")
