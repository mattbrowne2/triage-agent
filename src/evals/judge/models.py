from enum import StrEnum, auto

from pydantic import BaseModel, Field

from evals.models import TriageOutcome


class Criterion(StrEnum):
    EVIDENCE_GROUNDED = auto()
    CONFIDENCE_CALIBRATED = auto()
    NEXT_STEPS_ACTIONABLE = auto()
    TRUSTWORTHY = auto()


class Verdict(StrEnum):
    PASS = auto()
    FAIL = auto()


class CriterionVerdict(BaseModel):
    reasoning: str = Field(description="What in the investigation and report decides this criterion")
    verdict: Verdict


class JudgeVerdict(BaseModel):
    evidence_grounded: CriterionVerdict
    confidence_calibrated: CriterionVerdict
    next_steps_actionable: CriterionVerdict
    trustworthy: CriterionVerdict


class HumanLabels(BaseModel):
    evidence_grounded: Verdict
    confidence_calibrated: Verdict
    next_steps_actionable: Verdict
    trustworthy: Verdict
    notes: str


class LabelledReport(BaseModel):
    run_id: str
    experiment: str
    case_id: str
    alert: str
    outcome: TriageOutcome
    human: HumanLabels | None


class LabelSet(BaseModel):
    instructions: str
    reports: list[LabelledReport]


class CriterionAgreement(BaseModel):
    criterion: Criterion
    agreement: float
    both_pass: int
    both_fail: int
    judge_pass_human_fail: int
    judge_fail_human_pass: int


class Disagreement(BaseModel):
    case_id: str
    run_id: str
    criterion: Criterion
    judge: Verdict
    human: Verdict
    judge_reasoning: str
    human_notes: str


class CalibrationReport(BaseModel):
    judge_model: str
    labelled: int
    criteria: list[CriterionAgreement]
    disagreements: list[Disagreement]


class JudgedReport(BaseModel):
    report: LabelledReport
    human: HumanLabels
    judge: JudgeVerdict
