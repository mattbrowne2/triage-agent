from fastapi import FastAPI

from incident_triage.wiring import AgentFactory
from triage_api.routes import ops
from triage_api.routes.triages import build_triage_router
from triage_api.store import TriageStore


def create_app(build_agent: AgentFactory, max_steps: int) -> FastAPI:
    app = FastAPI(title="Incident triage API")
    app.include_router(ops.router)
    app.include_router(build_triage_router(build_agent, TriageStore(), max_steps))
    return app
