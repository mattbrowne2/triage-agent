from pathlib import Path
from typing import Any

import gradio as gr

from evals.judge.models import Criterion, HumanLabels, LabelledReport, LabelSet, Verdict
from evals.judge.prompt import load_judge_prompt
from triage_ui.render import masked, render_call, render_report, render_result, render_timeline


LABELS_PATH = Path("data/evals/judge_labels.json")

RUBRIC_HINTS = {
    Criterion.EVIDENCE_GROUNDED: (
        "Every fact in the report (timestamps, versions, counts, trace IDs, tickets) appears in a tool result. "
        "Open 'Raw result' to check. Anything invented or misquoted fails."
    ),
    Criterion.CONFIDENCE_CALIBRATED: (
        "High needs the failure mechanism and its trigger both seen in the logs, with timing that lines up. "
        "Medium when one link is inferred. Low for thin or conflicting evidence."
    ),
    Criterion.NEXT_STEPS_ACTIONABLE: (
        "Specific, follow from the findings, mitigation first when customers are failing, "
        "recommended rather than claimed as done."
    ),
    Criterion.TRUSTWORTHY: "At 3am, could you rely on this report without redoing the investigation?",
}


def build_labelling_tab(app: gr.Blocks) -> None:
    try:
        label_set = _load()
    except FileNotFoundError:
        gr.Markdown(f'No `{LABELS_PATH}` yet. Export reports first: `make judge-labels EXPERIMENTS="..."`.')
        return

    with gr.Row():
        with gr.Column(scale=5):
            alert = gr.Markdown()
            investigation = gr.HTML()
        with gr.Column(scale=4):
            report = gr.HTML()
        with gr.Column(scale=3, min_width=300):
            selector = gr.Dropdown(choices=_choices(label_set), value=_first_unlabelled(label_set), label="Report")
            progress = gr.Markdown()
            verdicts = [
                gr.Radio(
                    choices=[Verdict.PASS.value, Verdict.FAIL.value],
                    label=criterion.replace("_", " ").capitalize(),
                    info=RUBRIC_HINTS[criterion],
                )
                for criterion in Criterion
            ]
            notes = gr.Textbox(label="Notes", lines=4, placeholder="Why, especially for any fail")
            save = gr.Button("Save & next", variant="primary")
            status = gr.Markdown()
            with gr.Accordion("Full rubric", open=False):
                gr.Markdown(load_judge_prompt())

    view = [alert, investigation, report, *verdicts, notes, progress]
    app.load(_show, inputs=selector, outputs=view)
    selector.change(_show, inputs=selector, outputs=view)
    save.click(_save, inputs=[selector, *verdicts, notes], outputs=[status, selector])


def _show(index: int) -> tuple[Any, ...]:
    label_set = _load()
    item = label_set.reports[index]
    human = item.human
    verdicts = [getattr(human, criterion).value if human else None for criterion in Criterion]
    labelled = sum(report.human is not None for report in label_set.reports)
    return (
        _alert_markdown(item),
        _investigation(item),
        _report(item),
        *verdicts,
        human.notes if human else "",
        f"**{labelled} of {len(label_set.reports)} labelled**",
    )


def _save(index: int, *values: str | None) -> tuple[str, dict[str, Any]]:
    *verdicts, notes = values
    if any(verdict is None for verdict in verdicts):
        return "⚠️ Choose pass or fail for all four criteria before saving.", gr.update()
    label_set = _load()
    human = HumanLabels(
        **{criterion: Verdict(verdict) for criterion, verdict in zip(Criterion, verdicts, strict=True)},
        notes=notes or "",
    )
    label_set.reports[index] = label_set.reports[index].model_copy(update={"human": human})
    LABELS_PATH.write_text(label_set.model_dump_json(indent=2))
    remaining = [position for position, report in enumerate(label_set.reports) if report.human is None]
    if not remaining:
        message = f"✅ Saved. All {len(label_set.reports)} reports are labelled. Now run `make calibrate-judge`."
        return message, gr.update(choices=_choices(label_set), value=index)
    following = [position for position in remaining if position > index] or remaining
    return f"✅ Saved report {index + 1}.", gr.update(choices=_choices(label_set), value=following[0])


def _load() -> LabelSet:
    return LabelSet.model_validate_json(LABELS_PATH.read_text())


def _choices(label_set: LabelSet) -> list[tuple[str, int]]:
    return [
        (f"{'●' if report.human else '○'} {position + 1:02d} · {_arm(report)} · {report.case_id}", position)
        for position, report in enumerate(label_set.reports)
    ]


def _first_unlabelled(label_set: LabelSet) -> int:
    unlabelled = [position for position, report in enumerate(label_set.reports) if report.human is None]
    return unlabelled[0] if unlabelled else 0


def _arm(report: LabelledReport) -> str:
    return report.experiment.split("-")[1]


def _alert_markdown(item: LabelledReport) -> str:
    return f"**Alert** ({item.case_id}, {_arm(item)} arm)\n\n> {masked(item.alert)}"


def _investigation(item: LabelledReport) -> str:
    steps = []
    for call in item.outcome.tool_calls:
        steps.append(render_call(call.name, call.args))
        match call.result:
            case None:
                steps.append('<div class="step result"><p class="muted">Not executed (step limit).</p></div>')
            case result:
                raw = f"<details><summary>Raw result</summary><pre class='raw'>{masked(result)}</pre></details>"
                steps.append(render_result(call.name, result, footer=raw))
    return render_timeline(steps, running=False)


def _report(item: LabelledReport) -> str:
    match item.outcome.report:
        case None:
            return '<div class="report"><p class="muted">This run produced no report.</p></div>'
        case report:
            tickets = item.outcome.tickets
            return render_report(report, tickets[0] if tickets else None)
