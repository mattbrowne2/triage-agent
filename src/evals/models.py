from enum import StrEnum, auto

from pydantic import AwareDatetime, BaseModel, JsonValue

from incident_triage.models.alert import Alert
from incident_triage.models.jira import JiraIssue
from incident_triage.models.triage_report import TriageReport


class CaseSource(StrEnum):
    HUMAN = auto()
    MONITOR = auto()


class CaseType(StrEnum):
    CORRECT = auto()
    VAGUE = auto()
    WRONG_SERVICE = auto()
    WRONG_START_TIME = auto()
    FALSE_ALARM = auto()
    MISLEADING_CAUSE = auto()


class RootCauseExpectation(StrEnum):
    NAMES_TERMS = auto()
    NONE = auto()
    NOT_CHECKED = auto()


class ExpectedTriage(BaseModel):
    alert_confirmed: bool
    root_cause: RootCauseExpectation
    root_cause_terms: list[str]
    ruled_out_terms: list[str]
    related_incident: str | None
    must_not_cite: list[str]


class EvalCase(BaseModel):
    id: str
    source: CaseSource
    case_type: CaseType
    alert: str | Alert
    as_of: AwareDatetime
    expected: ExpectedTriage


class EvalSuite(BaseModel):
    cases: list[EvalCase]


class CaseInput(BaseModel):
    alert: str
    as_of: AwareDatetime


class ToolCallRecord(BaseModel):
    name: str
    args: dict[str, JsonValue]
    result: str | None


class TriageOutcome(BaseModel):
    report: TriageReport | None
    failure: str | None
    tool_calls: list[ToolCallRecord]
    incident_search_available: bool
    tickets: list[JiraIssue]


class CaseMetadata(BaseModel):
    case_id: str
    source: CaseSource
    case_type: CaseType


class ScoredExample(BaseModel):
    case_id: str
    source: str
    case_type: str
    scores: dict[str, float | None]


class MetricSummary(BaseModel):
    key: str
    mean: float | None
    scored: int
    not_applicable: int


class SliceSummary(BaseModel):
    name: str
    metrics: list[MetricSummary]


class ExperimentSummary(BaseModel):
    experiment: str
    arm: str
    overall: list[MetricSummary]
    slices: list[SliceSummary]


class ExperimentMetadata(BaseModel):
    arm: str
    dataset: str
    provider: str
    model: str
    reasoning_effort: str | None
    judge_model: str | None
