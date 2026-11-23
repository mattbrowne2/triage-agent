from fastapi.testclient import TestClient

from triage_api import main as main_module


def test_module_app_is_served_with_agent_built_from_settings() -> None:
    response = TestClient(main_module.app).get("/health")

    assert (response.status_code, response.json()) == (200, {"status": "ok"})
