from collections.abc import Callable
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from evals.judge.models import Criterion, CriterionVerdict, HumanLabels, JudgeVerdict, LabelledReport, Verdict
from evals.models import (
    CaseSource,
    CaseType,
    EvalCase,
    ExpectedTriage,
    RootCauseExpectation,
    ToolCallRecord,
    TriageOutcome,
)
from incident_triage.models.jira import JiraIssue, JiraPriority
from incident_triage.models.triage_report import RelatedIncident, TriageReport


class FakeLangSmithClient:
    def __init__(self, existing: set[str]) -> None:
        self.existing = existing
        self.uploads: list[tuple[str, list]] = []

    def has_dataset(self, *, dataset_name: str) -> bool:
        return dataset_name in self.existing

    def create_dataset(self, dataset_name: str, *, description: str) -> SimpleNamespace:
        self.existing.add(dataset_name)
        return SimpleNamespace(id=dataset_name)

    def create_examples(self, *, dataset_id: str, examples: list) -> None:
        self.uploads.append((dataset_id, examples))


class FakeExperimentResults:
    def __init__(self, experiment_name: str) -> None:
        self.experiment_name = experiment_name

    def __iter__(self):  # noqa: ANN204
        return iter([])


@pytest.fixture
def experiment_results_factory() -> Callable[[str], FakeExperimentResults]:
    def build(experiment_name: str) -> FakeExperimentResults:
        return FakeExperimentResults(experiment_name)

    return build


@pytest.fixture
def incident_expectation() -> ExpectedTriage:
    return ExpectedTriage(
        alert_confirmed=True,
        root_cause=RootCauseExpectation.NAMES_TERMS,
        root_cause_terms=["payment", "2.14.0"],
        ruled_out_terms=["inventory"],
        related_incident="INC-311",
        must_not_cite=["INC-298"],
    )


@pytest.fixture
def human_correct_case(incident_expectation: ExpectedTriage) -> EvalCase:
    return EvalCase(
        id="human-correct",
        source=CaseSource.HUMAN,
        case_type=CaseType.CORRECT,
        alert="ALR-8812: checkout-service 5xx error rate 18% (threshold 5%) since 2026-11-17T02:09:00Z",
        as_of=datetime(2026, 11, 17, 2, 15, tzinfo=UTC),
        expected=incident_expectation,
    )


@pytest.fixture
def outcome_factory(confirmed_triage_report: TriageReport) -> Callable[..., TriageOutcome]:
    def build(
        report_changes: dict[str, object] | None = None,
        search_available: bool = True,
        tool_calls: list[ToolCallRecord] | None = None,
        tickets: list[JiraIssue] | None = None,
    ) -> TriageOutcome:
        return TriageOutcome(
            report=confirmed_triage_report.model_copy(update=report_changes or {}),
            failure=None,
            tool_calls=tool_calls or [],
            incident_search_available=search_available,
            tickets=tickets or [],
        )

    return build


@pytest.fixture
def failed_outcome() -> TriageOutcome:
    return TriageOutcome(
        report=None,
        failure="Triage stopped after 25 steps without reaching a conclusion.",
        tool_calls=[],
        incident_search_available=True,
        tickets=[],
    )


@pytest.fixture
def confirmed_triage_report_related(confirmed_triage_report: TriageReport) -> RelatedIncident:
    return confirmed_triage_report.related_incidents[0]


@pytest.fixture
def as_dicts() -> Callable[[TriageOutcome, ExpectedTriage], tuple[dict, dict]]:
    def build(outcome: TriageOutcome, expected: ExpectedTriage) -> tuple[dict, dict]:
        return outcome.model_dump(mode="json"), expected.model_dump(mode="json")

    return build


@pytest.fixture
def langsmith_client_factory() -> Callable[..., FakeLangSmithClient]:
    def build(existing: set[str]) -> FakeLangSmithClient:
        return FakeLangSmithClient(existing)

    return build


@pytest.fixture
def judge_verdict_factory() -> Callable[..., "JudgeVerdict"]:
    def build(**overrides: Verdict) -> JudgeVerdict:
        verdicts = {criterion: overrides.get(criterion, Verdict.PASS) for criterion in Criterion}
        return JudgeVerdict(
            **{
                criterion: CriterionVerdict(reasoning=f"judge on {criterion}", verdict=verdict)
                for criterion, verdict in verdicts.items()
            }
        )

    return build


@pytest.fixture
def human_labels_factory() -> Callable[..., HumanLabels]:
    def build(**overrides: Verdict) -> HumanLabels:
        verdicts = {criterion: overrides.get(criterion, Verdict.PASS) for criterion in Criterion}
        return HumanLabels(**verdicts, notes="human notes")

    return build


@pytest.fixture
def labelled_report_factory(outcome_factory: Callable[..., TriageOutcome]) -> Callable[..., LabelledReport]:
    def build(case_id: str, human: HumanLabels | None, experiment: str = "triage-rag-1a2b") -> LabelledReport:
        return LabelledReport(
            run_id=f"run-{case_id}",
            experiment=experiment,
            case_id=case_id,
            alert=f"alert for {case_id}",
            outcome=outcome_factory(),
            human=human,
        )

    return build


@pytest.fixture
def filed_ticket() -> JiraIssue:
    return JiraIssue(
        id="10001",
        key="OPS-1",
        summary="Checkout failing: payment-service v2.14.0 rejects currency_code",
        description="Since 02:09 UTC checkout-service gets 400 unknown field 'currency_code'.",
        priority=JiraPriority.HIGHEST,
        service="payment-service",
        alert_key="alert:abc",
        created_at=datetime(2026, 11, 17, 2, 15, tzinfo=UTC),
    )
