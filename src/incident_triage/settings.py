from enum import StrEnum, auto
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class LLMProvider(StrEnum):
    ANTHROPIC = auto()
    OPENAI = auto()


class ReasoningEffort(StrEnum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: SecretStr = Field(alias="ANTHROPIC_API_KEY")
    OPENAI_API_KEY: SecretStr = Field(alias="OPENAI_API_KEY")
    LLM_PROVIDER: LLMProvider = Field(default=LLMProvider.ANTHROPIC, alias="LLM_PROVIDER")
    LLM_MODEL: str = Field(default="claude-sonnet-5-5", alias="LLM_MODEL")
    LLM_REASONING_EFFORT: ReasoningEffort | None = Field(default=None, alias="LLM_REASONING_EFFORT")
    MAX_AGENT_STEPS: int = Field(default=25, gt=0, alias="MAX_AGENT_STEPS")
    DATADOG_LOGS_PATH: Path = Field(
        default=Path("data/datadog_logs/payment_service_bad_deploy.json"), alias="DATADOG_LOGS_PATH"
    )
    INCIDENTS_PATH: Path = Field(default=Path("data/incidents/past_incidents.json"), alias="INCIDENTS_PATH")
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    INCIDENT_SEARCH_ENABLED: bool = Field(default=True, alias="INCIDENT_SEARCH_ENABLED")
    INCIDENT_MIN_SIMILARITY: float = Field(default=0.5, ge=-1, le=1, alias="INCIDENT_MIN_SIMILARITY")
    JUDGE_PROVIDER: LLMProvider = Field(default=LLMProvider.ANTHROPIC, alias="JUDGE_PROVIDER")
    JUDGE_MODEL: str = Field(default="claude-opus-5-5", alias="JUDGE_MODEL")
    JIRA_TICKETS_PATH: Path = Field(default=Path("data/jira/tickets.json"), alias="JIRA_TICKETS_PATH")

    @property
    def LLM_API_KEY(self) -> SecretStr:
        return self.api_key_for(self.LLM_PROVIDER)

    def api_key_for(self, provider: LLMProvider) -> SecretStr:
        match provider:
            case LLMProvider.ANTHROPIC:
                return self.ANTHROPIC_API_KEY
            case LLMProvider.OPENAI:
                return self.OPENAI_API_KEY


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv(".env")
    return Settings()
