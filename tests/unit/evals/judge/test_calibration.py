from collections.abc import Callable

from evals.judge.calibration import calibration_report, format_calibration, select_for_labelling
from evals.judge.models import (
    CalibrationReport,
    Criterion,
    CriterionAgreement,
    Disagreement,
    HumanLabels,
    JudgedReport,
    JudgeVerdict,
    LabelledReport,
    Verdict,
)
from evals.models import TriageOutcome


def test_select_for_labelling_keeps_the_first_run_with_a_report_per_experiment_and_case(
    labelled_report_factory: Callable[..., LabelledReport], failed_outcome: TriageOutcome
) -> None:
    first_vague = labelled_report_factory("human-vague", None)
    no_report = labelled_report_factory("human-correct", None).model_copy(update={"outcome": failed_outcome})
    with_report = labelled_report_factory("human-correct", None).model_copy(update={"run_id": "run-2"})
    second_vague = labelled_report_factory("human-vague", None).model_copy(update={"run_id": "run-3"})
    baseline_vague = labelled_report_factory("human-vague", None, experiment="triage-baseline-9f8e")

    selected = select_for_labelling([first_vague, no_report, with_report, second_vague, baseline_vague])

    assert [(report.experiment, report.case_id, report.run_id) for report in selected] == [
        ("triage-rag-1a2b", "human-vague", "run-human-vague"),
        ("triage-rag-1a2b", "human-correct", "run-2"),
        ("triage-baseline-9f8e", "human-vague", "run-human-vague"),
    ]


def test_calibration_report_counts_agreement_per_criterion_and_lists_each_disagreement(
    labelled_report_factory: Callable[..., LabelledReport],
    human_labels_factory: Callable[..., HumanLabels],
    judge_verdict_factory: Callable[..., JudgeVerdict],
) -> None:
    human_strict = human_labels_factory(confidence_calibrated=Verdict.FAIL)
    judged = [
        JudgedReport(
            report=labelled_report_factory("human-correct", human_strict),
            human=human_strict,
            judge=judge_verdict_factory(),
        ),
        JudgedReport(
            report=labelled_report_factory("human-vague", human_labels_factory(trustworthy=Verdict.FAIL)),
            human=human_labels_factory(trustworthy=Verdict.FAIL),
            judge=judge_verdict_factory(trustworthy=Verdict.FAIL),
        ),
    ]

    report = calibration_report("claude-opus-5-5", judged)

    assert report == CalibrationReport(
        judge_model="claude-opus-5-5",
        labelled=2,
        criteria=[
            CriterionAgreement(
                criterion=Criterion.EVIDENCE_GROUNDED,
                agreement=1.0,
                both_pass=2,
                both_fail=0,
                judge_pass_human_fail=0,
                judge_fail_human_pass=0,
            ),
            CriterionAgreement(
                criterion=Criterion.CONFIDENCE_CALIBRATED,
                agreement=0.5,
                both_pass=1,
                both_fail=0,
                judge_pass_human_fail=1,
                judge_fail_human_pass=0,
            ),
            CriterionAgreement(
                criterion=Criterion.NEXT_STEPS_ACTIONABLE,
                agreement=1.0,
                both_pass=2,
                both_fail=0,
                judge_pass_human_fail=0,
                judge_fail_human_pass=0,
            ),
            CriterionAgreement(
                criterion=Criterion.TRUSTWORTHY,
                agreement=1.0,
                both_pass=1,
                both_fail=1,
                judge_pass_human_fail=0,
                judge_fail_human_pass=0,
            ),
        ],
        disagreements=[
            Disagreement(
                case_id="human-correct",
                run_id="run-human-correct",
                criterion=Criterion.CONFIDENCE_CALIBRATED,
                judge=Verdict.PASS,
                human=Verdict.FAIL,
                judge_reasoning="judge on confidence_calibrated",
                human_notes="human notes",
            )
        ],
    )


def test_format_calibration_shows_agreement_table_then_each_disagreement(
    labelled_report_factory: Callable[..., LabelledReport],
    human_labels_factory: Callable[..., HumanLabels],
    judge_verdict_factory: Callable[..., JudgeVerdict],
) -> None:
    human = human_labels_factory(trustworthy=Verdict.FAIL)
    report = calibration_report(
        "claude-opus-5-5",
        [
            JudgedReport(
                report=labelled_report_factory("human-vague", human), human=human, judge=judge_verdict_factory()
            )
        ],
    )

    assert format_calibration(report) == (
        "judge: claude-opus-5-5 on 1 labelled reports\n"
        "criterion               agreement  both pass  both fail  judge pass/human fail  judge fail/human pass\n"
        "evidence_grounded       1.00       1          0          0                      0\n"
        "confidence_calibrated   1.00       1          0          0                      0\n"
        "next_steps_actionable   1.00       1          0          0                      0\n"
        "trustworthy             0.00       0          0          1                      0\n"
        "\n"
        "disagreements:\n"
        "- human-vague (run-human-vague) trustworthy: judge pass, human fail\n"
        "    judge: judge on trustworthy\n"
        "    human: human notes"
    )
