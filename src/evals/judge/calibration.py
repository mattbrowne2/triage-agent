from evals.judge.models import (
    CalibrationReport,
    Criterion,
    CriterionAgreement,
    Disagreement,
    JudgedReport,
    LabelledReport,
    Verdict,
)


def select_for_labelling(reports: list[LabelledReport]) -> list[LabelledReport]:
    selected: dict[tuple[str, str], LabelledReport] = {}
    for report in reports:
        key = (report.experiment, report.case_id)
        if report.outcome.report is not None and key not in selected:
            selected[key] = report
    return list(selected.values())


def calibration_report(judge_model: str, judged: list[JudgedReport]) -> CalibrationReport:
    return CalibrationReport(
        judge_model=judge_model,
        labelled=len(judged),
        criteria=[_agreement(criterion, judged) for criterion in Criterion],
        disagreements=[
            Disagreement(
                case_id=item.report.case_id,
                run_id=item.report.run_id,
                criterion=criterion,
                judge=getattr(item.judge, criterion).verdict,
                human=getattr(item.human, criterion),
                judge_reasoning=getattr(item.judge, criterion).reasoning,
                human_notes=item.human.notes,
            )
            for item in judged
            for criterion in Criterion
            if getattr(item.judge, criterion).verdict != getattr(item.human, criterion)
        ],
    )


def _agreement(criterion: Criterion, judged: list[JudgedReport]) -> CriterionAgreement:
    pairs = [(getattr(item.judge, criterion).verdict, getattr(item.human, criterion)) for item in judged]
    return CriterionAgreement(
        criterion=criterion,
        agreement=sum(judge == human for judge, human in pairs) / len(pairs),
        both_pass=pairs.count((Verdict.PASS, Verdict.PASS)),
        both_fail=pairs.count((Verdict.FAIL, Verdict.FAIL)),
        judge_pass_human_fail=pairs.count((Verdict.PASS, Verdict.FAIL)),
        judge_fail_human_pass=pairs.count((Verdict.FAIL, Verdict.PASS)),
    )


def format_calibration(report: CalibrationReport) -> str:
    header = (
        f"{'criterion':<24}{'agreement':<11}{'both pass':<11}{'both fail':<11}"
        f"{'judge pass/human fail':<23}judge fail/human pass"
    )
    rows = [
        f"{item.criterion:<24}{item.agreement:<11.2f}{item.both_pass:<11}{item.both_fail:<11}"
        f"{item.judge_pass_human_fail:<23}{item.judge_fail_human_pass}"
        for item in report.criteria
    ]
    disagreements = [
        f"- {item.case_id} ({item.run_id}) {item.criterion}: judge {item.judge}, human {item.human}\n"
        f"    judge: {item.judge_reasoning}\n"
        f"    human: {item.human_notes}"
        for item in report.disagreements
    ]
    return "\n".join(
        [f"judge: {report.judge_model} on {report.labelled} labelled reports", header, *rows, "", "disagreements:"]
        + disagreements
    )
