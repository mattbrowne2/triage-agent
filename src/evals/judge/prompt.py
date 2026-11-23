import json
from pathlib import Path

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from evals.models import ToolCallRecord
from incident_triage.models.triage_report import TriageReport


PROMPT_PATH = Path(__file__).parent / "prompts" / "judge.md"
NOT_EXECUTED = "(not executed)"


def load_judge_prompt() -> str:
    return PROMPT_PATH.read_text().strip()


def render_judge_input(alert: str, tool_calls: list[ToolCallRecord], report: TriageReport) -> str:
    steps = "".join(_render_call(number, call) for number, call in enumerate(tool_calls, start=1))
    return f"## Alert\n\n{alert}\n\n## Investigation\n\n{steps}## Report\n\n{report.model_dump_json(indent=2)}"


def judge_messages(alert: str, tool_calls: list[ToolCallRecord], report: TriageReport) -> list[BaseMessage]:
    return [
        SystemMessage(content=load_judge_prompt()),
        HumanMessage(content=render_judge_input(alert, tool_calls, report)),
    ]


def _render_call(number: int, call: ToolCallRecord) -> str:
    result = NOT_EXECUTED if call.result is None else call.result
    return f"### Tool call {number}: {call.name}\n\nArguments: {json.dumps(call.args)}\n\nResult:\n{result}\n\n"
