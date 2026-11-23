from pathlib import Path

from evals.models import CaseInput, EvalCase, EvalSuite
from incident_triage.agent.alert_message import render_alert


def load_suite(path: Path) -> EvalSuite:
    return EvalSuite.model_validate_json(path.read_text())


def alert_text(case: EvalCase) -> str:
    match case.alert:
        case str():
            return case.alert
        case alert:
            return render_alert(alert)


def case_input(case: EvalCase) -> CaseInput:
    return CaseInput(alert=alert_text(case), as_of=case.as_of)
