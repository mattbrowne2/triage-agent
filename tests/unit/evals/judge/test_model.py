from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from evals.judge.model import build_judge_chat_model
from incident_triage.settings import LLMProvider, Settings


def test_judge_chat_model_uses_its_own_provider_and_model_not_the_agents() -> None:
    settings = Settings(
        LLM_PROVIDER=LLMProvider.OPENAI,
        LLM_MODEL="gpt-6.1-sol",
        JUDGE_PROVIDER=LLMProvider.ANTHROPIC,
        JUDGE_MODEL="claude-opus-5-5",
    )

    judge = build_judge_chat_model(settings)

    assert (type(judge), judge.model, judge.anthropic_api_key.get_secret_value()) == (
        ChatAnthropic,
        "claude-opus-5-5",
        "test-anthropic-key",
    )


def test_judge_chat_model_can_be_an_openai_model() -> None:
    judge = build_judge_chat_model(Settings(JUDGE_PROVIDER=LLMProvider.OPENAI, JUDGE_MODEL="gpt-6.1-sol"))

    assert (type(judge), judge.model_name) == (ChatOpenAI, "gpt-6.1-sol")
