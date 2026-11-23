from pathlib import Path

from evals.judge.prompt import judge_messages, load_judge_prompt, render_judge_input
from evals.models import ToolCallRecord
from incident_triage.models.triage_report import TriageReport


PROMPTS_DIR = Path(__file__).parents[4] / "src" / "evals" / "judge" / "prompts"
ALERT = "ALR-8812: checkout-service 5xx error rate 18% (threshold 5%) since 2026-11-17T02:09:00Z"


def test_judge_prompt_is_read_from_prompts_directory() -> None:
    assert load_judge_prompt() == (PROMPTS_DIR / "judge.md").read_text().strip()


def test_judge_input_shows_alert_each_tool_call_with_its_result_and_the_report(
    confirmed_triage_report: TriageReport,
) -> None:
    tool_calls = [
        ToolCallRecord(name="query_logs", args={"service": "checkout-service"}, result='{"data": []}'),
        ToolCallRecord(name="query_logs", args={"service": "payment-service"}, result=None),
    ]

    assert render_judge_input(ALERT, tool_calls, confirmed_triage_report) == (
        f"## Alert\n\n{ALERT}\n\n"
        "## Investigation\n\n"
        '### Tool call 1: query_logs\n\nArguments: {"service": "checkout-service"}\n\nResult:\n{"data": []}\n\n'
        '### Tool call 2: query_logs\n\nArguments: {"service": "payment-service"}\n\nResult:\n(not executed)\n\n'
        f"## Report\n\n{confirmed_triage_report.model_dump_json(indent=2)}"
    )


def test_judge_messages_pair_the_rubric_with_the_rendered_input(confirmed_triage_report: TriageReport) -> None:
    messages = judge_messages(ALERT, [], confirmed_triage_report)

    assert [(message.type, message.content) for message in messages] == [
        ("system", load_judge_prompt()),
        ("human", render_judge_input(ALERT, [], confirmed_triage_report)),
    ]
