from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel, LanguageModelInput
from langchain_core.runnables import Runnable
from pydantic import BaseModel

from evals.judge.models import JudgeVerdict
from incident_triage.settings import Settings


def build_judge_chat_model(settings: Settings) -> BaseChatModel:
    return init_chat_model(
        model=settings.JUDGE_MODEL,
        model_provider=settings.JUDGE_PROVIDER,
        api_key=settings.api_key_for(settings.JUDGE_PROVIDER).get_secret_value(),
    )


def build_judge(settings: Settings) -> Runnable[LanguageModelInput, dict | BaseModel]:
    return build_judge_chat_model(settings).with_structured_output(JudgeVerdict, method="json_schema")
