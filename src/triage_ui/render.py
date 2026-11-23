from html import escape

from pydantic import JsonValue, ValidationError

from incident_triage.models.incident import Resolution
from incident_triage.models.incident_search import IncidentSearchResponse
from incident_triage.models.jira import JiraCreateResponse, JiraIssue
from incident_triage.models.log_patterns import LogPatternSummary
from incident_triage.models.log_search import LogSearchResponse
from incident_triage.models.tools import ToolName
from incident_triage.models.triage_report import TriageReport
from incident_triage.pii import EMAIL_PATTERN


LOG_ROWS_SHOWN = 8
ARGUMENT_CHARS_SHOWN = 140
TOOL_ICONS = {
    ToolName.QUERY_LOGS: "🔎",
    ToolName.SUMMARIZE_LOG_PATTERNS: "🧭",
    ToolName.SEARCH_PAST_INCIDENTS: "📚",
    ToolName.CREATE_JIRA_TICKET: "🎫",
}


def masked(text: str) -> str:
    return escape(EMAIL_PATTERN.sub("‹email›", text))


def status_badge(status: str) -> str:
    return f'<span class="badge status-{escape(status)}">{escape(status)}</span>'


def render_thought(text: str) -> str:
    return f'<div class="step thought"><div class="step-head">💭 Agent</div><p>{masked(text)}</p></div>'


def render_call(name: str, args: dict[str, JsonValue]) -> str:
    chips = "".join(
        f'<span class="chip"><b>{escape(key)}</b> {masked(_shortened(str(value)))}</span>'
        for key, value in args.items()
        if value is not None
    )
    icon = TOOL_ICONS[ToolName(name)]
    return f'<div class="step call"><div class="step-head">{icon} <code>{escape(name)}</code></div>{chips}</div>'


def render_result(name: str, content: str, footer: str = "") -> str:
    try:
        body = _result_body(ToolName(name), content)
    except ValidationError:
        return f'<div class="step result error"><div class="step-head">⚠️ Tool error</div><p>{masked(content)}</p></div>'
    return f'<div class="step result">{body}{footer}</div>'


def render_timeline(steps: list[str], running: bool) -> str:
    finished = "Investigation complete" if steps else "Ready"
    status = '<span class="pulse"></span> Investigating…' if running else finished
    body = "".join(steps) or '<p class="muted">Pick a case or paste an alert, then run the triage.</p>'
    return f'<div class="timeline"><div class="timeline-head">{status}</div>{body}</div>'


def render_failure(message: str) -> str:
    head = '<div class="report-head failed">Triage ended without a report</div>'
    return f'<div class="report">{head}<p>{masked(message)}</p></div>'


def render_report(report: TriageReport, ticket: JiraIssue | None) -> str:
    verdict = (
        '<span class="badge ok">✓ Alert confirmed</span>'
        if report.alert_confirmed
        else '<span class="badge warn">✗ Alert not confirmed</span>'
    )
    confidence = f'<span class="badge confidence-{report.confidence}">{report.confidence} confidence</span>'
    discrepancy = (
        f'<p class="discrepancy"><b>What the alert got wrong:</b> {masked(report.alert_discrepancy)}</p>'
        if report.alert_discrepancy
        else ""
    )
    no_root_cause = "<i>No root cause: the evidence does not support one.</i>"
    root_cause = masked(report.root_cause) if report.root_cause else no_root_cause
    related = "".join(
        f'<li><b>{escape(item.key)}</b>: {masked(item.why_similar)}<br><span class="muted">Differs: '
        f"{masked(item.what_differs)}</span> {_links(item.change_urls)}</li>"
        for item in report.related_incidents
    )
    return (
        f'<div class="report"><div class="report-head">{verdict}{confidence}</div>{discrepancy}'
        f'<h3>Root cause</h3><p class="root-cause">{root_cause}</p>'
        f"<h3>Impact</h3><p>{masked(report.impact)}</p>"
        f"<h3>Next steps</h3><ol>{_items(report.next_steps)}</ol>"
        f"<h3>Evidence</h3><ul>{_items(report.evidence)}</ul>"
        f"<h3>Ruled out</h3><ul>{_items(report.ruled_out)}</ul>"
        f"{f'<h3>Related past incidents</h3><ul>{related}</ul>' if related else ''}"
        f"{render_ticket(ticket)}</div>"
    )


def render_ticket(ticket: JiraIssue | None) -> str:
    match ticket:
        case None:
            return '<div class="ticket none">No Jira ticket filed.</div>'
        case issue:
            return (
                f'<div class="ticket"><div class="ticket-head"><span class="ticket-key">{escape(issue.key)}</span>'
                f'<span class="badge priority-{issue.priority.lower()}">{issue.priority}</span>'
                f'<span class="chip">{escape(issue.service)}</span></div>'
                f'<div class="ticket-summary">{masked(issue.summary)}</div>'
                f"<details><summary>Description</summary><pre>{masked(issue.description)}</pre></details></div>"
            )


def _result_body(tool: ToolName, content: str) -> str:
    match tool:
        case ToolName.QUERY_LOGS:
            return _logs(LogSearchResponse.model_validate_json(content))
        case ToolName.SUMMARIZE_LOG_PATTERNS:
            return _patterns(LogPatternSummary.model_validate_json(content))
        case ToolName.SEARCH_PAST_INCIDENTS:
            return _incidents(IncidentSearchResponse.model_validate_json(content))
        case ToolName.CREATE_JIRA_TICKET:
            response = JiraCreateResponse.model_validate_json(content)
            link = f'<span class="muted">{escape(response.self_url)}</span>'
            return f'<div class="filed">🎫 Filed <b>{escape(response.key)}</b> {link}</div>'


def _logs(response: LogSearchResponse) -> str:
    rows = "".join(
        f"<tr><td>{log.attributes.timestamp:%H:%M:%S}</td><td>{escape(log.attributes.service)}</td>"
        f"<td>{status_badge(log.attributes.status)}</td><td>{masked(log.attributes.message)}</td></tr>"
        for log in response.data[:LOG_ROWS_SHOWN]
    )
    shown = min(len(response.data), LOG_ROWS_SHOWN)
    return (
        f'<div class="muted">{response.meta.total_matches} matching logs, showing {shown}</div>'
        f"<table><tr><th>Time</th><th>Service</th><th>Status</th><th>Message</th></tr>{rows}</table>"
    )


def _patterns(summary: LogPatternSummary) -> str:
    rows = "".join(
        f'<tr class="row-{pattern.status}"><td>{escape(pattern.service)}</td><td>{status_badge(pattern.status)}</td>'
        f"<td class='count'>{pattern.count}</td><td>{pattern.first_seen:%H:%M}–{pattern.last_seen:%H:%M}</td>"
        f"<td>{masked(pattern.template)}</td></tr>"
        for pattern in summary.patterns
    )
    return (
        f'<div class="muted">{summary.total_logs} logs in {len(summary.patterns)} patterns</div>'
        f"<table><tr><th>Service</th><th>Status</th><th>Count</th><th>Seen</th><th>Pattern</th></tr>{rows}</table>"
    )


def _incidents(response: IncidentSearchResponse) -> str:
    if not response.matches:
        return '<div class="muted">No similar past incidents.</div>'
    cards = "".join(
        f'<div class="incident"><div><b>{escape(match.incident.key)}</b> {masked(match.incident.title)}</div>'
        f'<div class="similarity"><span style="width:{match.similarity * 100:.0f}%"></span></div>'
        f'<div class="muted">similarity {match.similarity:.2f} · '
        f"{'resolved: ' + masked(match.incident.resolution.fix) if match.incident.resolution else 'still open'}</div>"
        f"{_change_links(match.incident.resolution)}</div>"
        for match in response.matches
    )
    return cards


def _change_links(resolution: Resolution | None) -> str:
    match resolution:
        case None:
            return ""
        case resolved:
            return _links([change.url for change in resolved.changes])


def _shortened(text: str) -> str:
    return text if len(text) <= ARGUMENT_CHARS_SHOWN else f"{text[:ARGUMENT_CHARS_SHOWN]}…"


def _items(items: list[str]) -> str:
    return "".join(f"<li>{masked(item)}</li>" for item in items)


def _links(urls: list[str]) -> str:
    return " ".join(
        f'<a href="{escape(url)}" target="_blank">{escape("/".join(url.rsplit("/", 2)[-2:]))}</a>' for url in urls
    )
