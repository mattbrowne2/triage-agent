from langchain.agents.structured_output import ProviderStrategy, ToolStrategy

from incident_triage.agent.response_format import REPORT_SUBMITTED, build_response_format
from incident_triage.models.triage_report import TriageReport
from incident_triage.settings import LLMProvider


def test_anthropic_uses_native_structured_output() -> None:
    assert build_response_format(LLMProvider.ANTHROPIC) == ProviderStrategy(TriageReport)


def test_openai_submits_the_report_as_a_tool_call() -> None:
    assert build_response_format(LLMProvider.OPENAI) == ToolStrategy(
        TriageReport, tool_message_content=REPORT_SUBMITTED
    )
