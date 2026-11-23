from fastapi import APIRouter, BackgroundTasks, HTTPException, Response, status

from incident_triage.models.alert import Alert
from incident_triage.wiring import AgentFactory
from triage_api.errors import TriageNotFoundError
from triage_api.models import Triage
from triage_api.store import TriageStore
from triage_api.worker import run_triage


def build_triage_router(build_agent: AgentFactory, store: TriageStore, max_steps: int) -> APIRouter:
    router = APIRouter()

    @router.post("/alerts", status_code=status.HTTP_202_ACCEPTED)
    def receive_alert(alert: Alert, response: Response, background_tasks: BackgroundTasks) -> Triage:
        triage, created = store.add(alert)
        if created:
            background_tasks.add_task(run_triage, build_agent(alert.id), store, alert.id, max_steps)
        else:
            response.status_code = status.HTTP_200_OK
        return triage

    @router.get("/triages")
    def list_triages() -> list[Triage]:
        return store.list()

    @router.get("/triages/{alert_id}")
    def get_triage(alert_id: str) -> Triage:
        try:
            return store.get(alert_id)
        except TriageNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return router
