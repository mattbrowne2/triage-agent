from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from incident_triage.settings import Settings


def build_chat_model(settings: Settings) -> BaseChatModel:
    return init_chat_model(
        model=settings.LLM_MODEL,
        model_provider=settings.LLM_PROVIDER,
        api_key=settings.LLM_API_KEY.get_secret_value(),
        reasoning_effort=settings.LLM_REASONING_EFFORT,
    )
