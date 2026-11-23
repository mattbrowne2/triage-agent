from incident_triage.settings import get_settings
from incident_triage.wiring import build_agent_factory
from triage_api.app import create_app


_settings = get_settings()

app = create_app(build_agent_factory(_settings), _settings.MAX_AGENT_STEPS)
