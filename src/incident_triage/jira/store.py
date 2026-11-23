from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from threading import Lock

from incident_triage.jira.errors import TicketContainsPersonalDataError
from incident_triage.models.jira import JiraIssue, JiraIssueArchive, TicketRequest
from incident_triage.pii import find_emails


PROJECT_KEY = "OPS"
FIRST_ISSUE_ID = 10001

type Clock = Callable[[], datetime]


class JiraStore:
    def __init__(self, clock: Clock, issues: list[JiraIssue]) -> None:
        self._clock = clock
        self._issues = list(issues)
        self._lock = Lock()

    def create(self, alert_key: str, request: TicketRequest) -> tuple[JiraIssue, bool]:
        emails = find_emails(f"{request.summary}\n{request.description}")
        if emails:
            raise TicketContainsPersonalDataError(len(emails))
        with self._lock:
            existing = [issue for issue in self._issues if issue.alert_key == alert_key]
            if existing:
                return existing[0], False
            number = len(self._issues) + 1
            issue = JiraIssue(
                id=str(FIRST_ISSUE_ID + number - 1),
                key=f"{PROJECT_KEY}-{number}",
                summary=request.summary,
                description=request.description,
                priority=request.priority,
                service=request.service,
                alert_key=alert_key,
                created_at=self._clock(),
            )
            self._issues.append(issue)
            self._saved()
            return issue, True

    def issues(self) -> list[JiraIssue]:
        return list(self._issues)

    def _saved(self) -> None:
        return None


class FileJiraStore(JiraStore):
    def __init__(self, path: Path, clock: Clock) -> None:
        self._path = path
        try:
            issues = JiraIssueArchive.model_validate_json(path.read_text()).issues
        except FileNotFoundError:
            issues = []
        super().__init__(clock, issues)

    def _saved(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(JiraIssueArchive(issues=self._issues).model_dump_json(indent=2))
