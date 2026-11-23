import logging

from langgraph.graph.state import CompiledStateGraph

from incident_triage.agent.alert_message import render_alert
from incident_triage.models.triage_report import TriageReport
from incident_triage.runner import stream_triage
from triage_api.models import TriageStatus
from triage_api.store import TriageStore


logger = logging.getLogger(__name__)


def run_triage(agent: CompiledStateGraph, store: TriageStore, alert_id: str, max_steps: int) -> None:
    triage = store.get(alert_id)
    try:
        outcome = list(stream_triage(agent, render_alert(triage.alert), max_steps))[-1]
    except Exception as error:
        logger.exception("Triage for alert %s failed", alert_id)
        failure = f"{type(error).__name__}: {error}"
        store.save(triage.model_copy(update={"status": TriageStatus.FAILED, "error": failure}))
        return
    match outcome:
        case TriageReport():
            store.save(triage.model_copy(update={"status": TriageStatus.COMPLETED, "report": outcome}))
        case _:
            store.save(triage.model_copy(update={"status": TriageStatus.FAILED, "error": outcome.text}))
