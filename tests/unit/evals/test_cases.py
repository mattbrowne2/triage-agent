from pathlib import Path

from evals.cases import alert_text, case_input, load_suite
from evals.models import CaseInput, CaseSource, CaseType, EvalCase
from incident_triage.agent.alert_message import render_alert
from incident_triage.models.alert import Alert


CASES_PATH = Path(__file__).parents[3] / "data" / "evals" / "triage_cases.json"


def test_suite_covers_each_alert_source_and_case_type() -> None:
    suite = load_suite(CASES_PATH)

    assert [(case.id, case.source, case.case_type) for case in suite.cases] == [
        ("human-correct", CaseSource.HUMAN, CaseType.CORRECT),
        ("human-vague", CaseSource.HUMAN, CaseType.VAGUE),
        ("human-wrong-service", CaseSource.HUMAN, CaseType.WRONG_SERVICE),
        ("human-wrong-start-time", CaseSource.HUMAN, CaseType.WRONG_START_TIME),
        ("human-false-alarm", CaseSource.HUMAN, CaseType.FALSE_ALARM),
        ("human-misleading-cause", CaseSource.HUMAN, CaseType.MISLEADING_CAUSE),
        ("monitor-checkout", CaseSource.MONITOR, CaseType.CORRECT),
        ("monitor-web-frontend", CaseSource.MONITOR, CaseType.CORRECT),
    ]


def test_alert_text_is_the_human_text_as_written(human_correct_case: EvalCase) -> None:
    assert alert_text(human_correct_case) == (
        "ALR-8812: checkout-service 5xx error rate 18% (threshold 5%) since 2026-11-17T02:09:00Z"
    )


def test_alert_text_renders_monitor_alerts_as_the_api_does(
    human_correct_case: EvalCase, checkout_error_rate_alert: Alert
) -> None:
    monitor_case = human_correct_case.model_copy(update={"alert": checkout_error_rate_alert})

    assert alert_text(monitor_case) == render_alert(checkout_error_rate_alert)


def test_case_input_carries_alert_text_and_investigation_time(human_correct_case: EvalCase) -> None:
    assert case_input(human_correct_case) == CaseInput(
        alert="ALR-8812: checkout-service 5xx error rate 18% (threshold 5%) since 2026-11-17T02:09:00Z",
        as_of=human_correct_case.as_of,
    )
