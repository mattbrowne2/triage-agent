import pytest
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from incident_triage.agent.chat_model import build_chat_model
from incident_triage.settings import Settings


def test_builds_anthropic_chat_model_with_configured_model_key_and_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_MODEL", "claude-sonnet-5-5")
    monkeypatch.setenv("LLM_REASONING_EFFORT", "medium")

    model = build_chat_model(Settings())

    assert (type(model), model.model, model.anthropic_api_key.get_secret_value(), model.reasoning_effort) == (
        ChatAnthropic,
        "claude-sonnet-5-5",
        "test-anthropic-key",
        "medium",
    )


def test_builds_openai_chat_model_with_configured_model_key_and_effort(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_MODEL", "gpt-6.1-sol")
    monkeypatch.setenv("LLM_REASONING_EFFORT", "low")

    model = build_chat_model(Settings())

    assert (type(model), model.model_name, model.openai_api_key.get_secret_value(), model.reasoning_effort) == (
        ChatOpenAI,
        "gpt-6.1-sol",
        "test-openai-key",
        "low",
    )


def test_unset_effort_leaves_the_provider_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("LLM_REASONING_EFFORT", raising=False)

    model = build_chat_model(Settings())

    assert model.reasoning_effort is None
