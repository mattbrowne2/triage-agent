from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import gradio as gr
from langchain_core.messages import AIMessage, ToolMessage

from evals.cases import alert_text, load_suite
from incident_triage.agent.chat_model import build_chat_model
from incident_triage.agent.triage_agent import build_triage_agent
from incident_triage.jira.store import JiraStore
from incident_triage.log_store.repository import LogRepository
from incident_triage.log_store.snapshot import snapshot
from incident_triage.models.datadog import LogArchive
from incident_triage.models.triage_report import TriageReport
from incident_triage.runner import stream_triage
from incident_triage.settings import get_settings
from incident_triage.tools.create_jira_ticket import build_create_jira_ticket_tool
from incident_triage.tools.query_logs import build_query_logs_tool
from incident_triage.tools.summarize_log_patterns import build_summarize_log_patterns_tool
from incident_triage.wiring import alert_key_for, incident_tools
from triage_ui.labelling import build_labelling_tab
from triage_ui.render import (
    render_call,
    render_failure,
    render_report,
    render_result,
    render_thought,
    render_timeline,
)


_settings = get_settings()

CASES_PATH = Path("data/evals/triage_cases.json")
CSS_PATH = Path(__file__).parent / "styles.css"
DEFAULT_AS_OF = "2026-11-17T02:15:00Z"

ARCHIVE = LogArchive.model_validate_json(_settings.DATADOG_LOGS_PATH.read_text())
MODEL = build_chat_model(_settings)
INCIDENT_TOOLS = incident_tools(_settings)
CASES = {case.id: case for case in load_suite(CASES_PATH).cases}
JIRA = JiraStore(clock=lambda: datetime.now(UTC), issues=[])


def triage(alert: str, as_of: str) -> Iterator[tuple[str, str]]:
    investigated_at = datetime.fromisoformat(as_of)
    repository = LogRepository(snapshot(ARCHIVE, investigated_at))
    alert_key = alert_key_for(f"{alert}@{as_of}")
    tools = [
        build_query_logs_tool(repository),
        build_summarize_log_patterns_tool(repository),
        *INCIDENT_TOOLS,
        build_create_jira_ticket_tool(JIRA, alert_key),
    ]
    agent = build_triage_agent(MODEL, tools, _settings.LLM_PROVIDER)
    steps: list[str] = []
    tool_names: dict[str, str] = {}
    report_html = ""
    yield render_timeline(steps, running=True), report_html
    try:
        for item in stream_triage(agent, alert, _settings.MAX_AGENT_STEPS):
            match item:
                case TriageReport() as report:
                    tickets = [issue for issue in JIRA.issues() if issue.alert_key == alert_key]
                    report_html = render_report(report, tickets[0] if tickets else None)
                case AIMessage(tool_calls=[_, *_]) as message:
                    if message.text:
                        steps.append(render_thought(message.text))
                    for call in message.tool_calls:
                        tool_names[call["id"]] = call["name"]
                        if call["name"] != TriageReport.__name__:
                            steps.append(render_call(call["name"], call["args"]))
                case ToolMessage() as message if tool_names[message.tool_call_id] != TriageReport.__name__:
                    steps.append(render_result(tool_names[message.tool_call_id], message.text))
                case AIMessage(content=str() as text) if text.startswith("Triage "):
                    report_html = render_failure(text)
            yield render_timeline(steps, running=True), report_html
    except Exception as error:
        report_html = render_failure(f"{type(error).__name__}: {error}")
    yield render_timeline(steps, running=False), report_html


def load_case(case_id: str) -> tuple[str, str]:
    case = CASES[case_id]
    return alert_text(case), case.as_of.isoformat().replace("+00:00", "Z")


def header() -> str:
    search = "on" if INCIDENT_TOOLS else "off"
    return (
        '<div class="app-header"><h1>🚨 Incident Triage Agent</h1>'
        "<p>Investigates a production alert against Datadog-style logs, checks past incidents, files a Jira ticket "
        "and reports what an on-call engineer needs at 3am.</p><p>"
        f'<span class="chip">model {_settings.LLM_MODEL}</span>'
        f'<span class="chip">past-incident search {search}</span>'
        '<span class="chip">traced in LangSmith</span></p></div>'
    )


def build_app() -> gr.Blocks:
    with gr.Blocks(title="Incident Triage Agent", fill_width=True) as app:
        gr.HTML(header())
        with gr.Tab("Triage"):
            build_triage_tab()
        with gr.Tab("Label reports for judge calibration"):
            build_labelling_tab(app)
    return app


def build_triage_tab() -> None:
    with gr.Row():
        with gr.Column(scale=2, min_width=280):
            case = gr.Dropdown(choices=list(CASES), label="Load an eval case", value=None)
            alert = gr.Textbox(label="Alert", lines=4, placeholder="Paste an alert, or load a case above")
            as_of = gr.Textbox(label="Investigating as of (UTC)", value=DEFAULT_AS_OF)
            run = gr.Button("Run triage", variant="primary")
            gr.Markdown(
                "The agent only sees logs written before the *as of* time, as on-call would. "
                "Customer emails are masked in this view."
            )
        with gr.Column(scale=5):
            timeline = gr.HTML(render_timeline([], running=False))
        with gr.Column(scale=4):
            report = gr.HTML('<div class="report"><p class="muted">The triage report appears here.</p></div>')
    case.change(load_case, inputs=case, outputs=[alert, as_of])
    run.click(triage, inputs=[alert, as_of], outputs=[timeline, report])


def main() -> None:
    build_app().launch(theme=gr.themes.Soft(primary_hue="indigo"), css=CSS_PATH.read_text())


if __name__ == "__main__":
    main()
