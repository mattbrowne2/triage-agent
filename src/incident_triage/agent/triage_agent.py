from collections.abc import Sequence

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.graph.state import CompiledStateGraph

from incident_triage.agent.prompt_loader import load_system_prompt
from incident_triage.agent.response_format import build_response_format
from incident_triage.settings import LLMProvider


AGENT_NAME = "incident_triage"


def build_triage_agent(model: BaseChatModel, tools: Sequence[BaseTool], provider: LLMProvider) -> CompiledStateGraph:
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=load_system_prompt(),
        response_format=build_response_format(provider),
        name=AGENT_NAME,
    )
