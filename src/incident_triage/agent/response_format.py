from langchain.agents.structured_output import ProviderStrategy, ToolStrategy

from incident_triage.models.triage_report import TriageReport
from incident_triage.settings import LLMProvider


REPORT_SUBMITTED = "Triage report submitted."


def build_response_format(provider: LLMProvider) -> ProviderStrategy[TriageReport] | ToolStrategy[TriageReport]:
    match provider:
        case LLMProvider.ANTHROPIC:
            return ProviderStrategy(TriageReport)
        case LLMProvider.OPENAI:
            return ToolStrategy(TriageReport, tool_message_content=REPORT_SUBMITTED)
