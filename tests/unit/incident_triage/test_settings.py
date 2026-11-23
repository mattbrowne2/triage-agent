from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from incident_triage.settings import LLMProvider, ReasoningEffort, Settings


def test_settings_load_from_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-5.2")
    monkeypatch.setenv("LLM_REASONING_EFFORT", "low")
    monkeypatch.setenv("MAX_AGENT_STEPS", "12")
    monkeypatch.setenv("DATADOG_LOGS_PATH", "data/datadog_logs/other.json")
    monkeypatch.setenv("INCIDENTS_PATH", "data/incidents/other.json")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-large")
    monkeypatch.setenv("INCIDENT_SEARCH_ENABLED", "true")
    monkeypatch.setenv("INCIDENT_MIN_SIMILARITY", "0.5")
    monkeypatch.setenv("JUDGE_PROVIDER", "openai")
    monkeypatch.setenv("JUDGE_MODEL", "gpt-6.1-sol")
    monkeypatch.setenv("JIRA_TICKETS_PATH", "data/jira/other.json")

    settings = Settings()

    assert settings == Settings(
        ANTHROPIC_API_KEY=SecretStr("test-anthropic-key"),
        OPENAI_API_KEY=SecretStr("test-openai-key"),
        LLM_PROVIDER=LLMProvider.OPENAI,
        LLM_MODEL="gpt-5.2",
        LLM_REASONING_EFFORT=ReasoningEffort.LOW,
        MAX_AGENT_STEPS=12,
        DATADOG_LOGS_PATH=Path("data/datadog_logs/other.json"),
        INCIDENTS_PATH=Path("data/incidents/other.json"),
        EMBEDDING_MODEL="text-embedding-3-large",
        INCIDENT_SEARCH_ENABLED=True,
        INCIDENT_MIN_SIMILARITY=0.5,
        JUDGE_PROVIDER=LLMProvider.OPENAI,
        JUDGE_MODEL="gpt-6.1-sol",
        JIRA_TICKETS_PATH=Path("data/jira/other.json"),
    )


@pytest.mark.usefixtures("optional_settings_unset")
def test_settings_default_to_anthropic_bad_deploy_scenario_and_incident_search_on() -> None:
    settings = Settings()

    assert settings == Settings(
        ANTHROPIC_API_KEY=SecretStr("test-anthropic-key"),
        OPENAI_API_KEY=SecretStr("test-openai-key"),
        LLM_PROVIDER=LLMProvider.ANTHROPIC,
        LLM_MODEL="claude-sonnet-5-5",
        LLM_REASONING_EFFORT=None,
        MAX_AGENT_STEPS=25,
        DATADOG_LOGS_PATH=Path("data/datadog_logs/payment_service_bad_deploy.json"),
        INCIDENTS_PATH=Path("data/incidents/past_incidents.json"),
        EMBEDDING_MODEL="text-embedding-3-small",
        INCIDENT_SEARCH_ENABLED=True,
        INCIDENT_MIN_SIMILARITY=0.5,
        JUDGE_PROVIDER=LLMProvider.ANTHROPIC,
        JUDGE_MODEL="claude-opus-5-5",
        JIRA_TICKETS_PATH=Path("data/jira/tickets.json"),
    )


@pytest.mark.parametrize(
    ("provider", "expected_key"),
    [
        (LLMProvider.ANTHROPIC, SecretStr("test-anthropic-key")),
        (LLMProvider.OPENAI, SecretStr("test-openai-key")),
    ],
)
def test_llm_api_key_belongs_to_selected_provider(
    monkeypatch: pytest.MonkeyPatch, provider: LLMProvider, expected_key: SecretStr
) -> None:
    monkeypatch.setenv("LLM_PROVIDER", provider)

    assert Settings().LLM_API_KEY == expected_key


def test_missing_api_key_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY")

    with pytest.raises(ValidationError):
        Settings()


def test_api_key_for_returns_the_key_of_any_provider() -> None:
    settings = Settings()

    assert (settings.api_key_for(LLMProvider.ANTHROPIC), settings.api_key_for(LLMProvider.OPENAI)) == (
        SecretStr("test-anthropic-key"),
        SecretStr("test-openai-key"),
    )
