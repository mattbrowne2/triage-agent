from pathlib import Path

from langchain_core.tools import StructuredTool

from incident_triage.jira.store import JiraStore
from incident_triage.models.jira import JiraCreateResponse, TicketRequest
from incident_triage.models.tools import ToolName


DESCRIPTIONS_DIR = Path(__file__).parents[4] / "src" / "incident_triage" / "tools" / "descriptions"


def test_tool_exposes_name_description_and_argument_schema(create_jira_ticket_tool: StructuredTool) -> None:
    assert (
        create_jira_ticket_tool.name,
        create_jira_ticket_tool.description,
        create_jira_ticket_tool.args_schema,
    ) == (
        ToolName.CREATE_JIRA_TICKET,
        (DESCRIPTIONS_DIR / "create_jira_ticket.md").read_text().strip(),
        TicketRequest,
    )


def test_tool_returns_jira_create_issue_response_json(
    create_jira_ticket_tool: StructuredTool, rollback_ticket_request: TicketRequest
) -> None:
    result = create_jira_ticket_tool.invoke(rollback_ticket_request.model_dump(mode="json"))

    assert result == ('{"id":"10001","key":"OPS-1","self":"https://jira.example.com/rest/api/3/issue/10001"}')
    assert JiraCreateResponse.model_validate_json(result).key == "OPS-1"


def test_tool_files_only_one_ticket_per_alert(
    create_jira_ticket_tool: StructuredTool, rollback_ticket_request: TicketRequest, jira_store: JiraStore
) -> None:
    first = create_jira_ticket_tool.invoke(rollback_ticket_request.model_dump(mode="json"))
    second = create_jira_ticket_tool.invoke(rollback_ticket_request.model_dump(mode="json"))

    assert (first == second, len(jira_store.issues())) == (True, 1)


def test_tool_tells_the_agent_to_remove_customer_emails(
    create_jira_ticket_tool: StructuredTool, rollback_ticket_request: TicketRequest
) -> None:
    leaking = rollback_ticket_request.model_copy(update={"description": "Failing for priya.nguyen@example.com"})

    result = create_jira_ticket_tool.invoke(leaking.model_dump(mode="json"))

    assert result == (
        "Ticket rejected: it contains 1 customer email addresses. "
        "Remove customer personal data from the summary and description, then file it again."
    )
