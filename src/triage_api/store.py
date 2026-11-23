from incident_triage.models.alert import Alert
from triage_api.errors import TriageNotFoundError
from triage_api.models import Triage


class TriageStore:
    def __init__(self) -> None:
        self._triages: dict[str, Triage] = {}

    def add(self, alert: Alert) -> tuple[Triage, bool]:
        queued = Triage(alert=alert)
        stored = self._triages.setdefault(alert.id, queued)
        return stored, stored is queued

    def get(self, alert_id: str) -> Triage:
        try:
            return self._triages[alert_id]
        except KeyError as error:
            raise TriageNotFoundError(alert_id) from error

    def list(self) -> list[Triage]:
        return list(self._triages.values())

    def save(self, triage: Triage) -> None:
        self._triages[triage.alert.id] = triage
