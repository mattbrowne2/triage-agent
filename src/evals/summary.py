from collections.abc import Callable

from langsmith.evaluation._runner import ExperimentResultRow

from evals.models import CaseMetadata, ExperimentSummary, MetricSummary, ScoredExample, SliceSummary


COLUMN_WIDTH = 13
METRIC_WIDTH = 32


def scored_example(row: ExperimentResultRow) -> ScoredExample:
    metadata = CaseMetadata.model_validate(row["example"].metadata)
    return ScoredExample(
        case_id=metadata.case_id,
        source=metadata.source,
        case_type=metadata.case_type,
        scores={result.key: result.score for result in row["evaluation_results"]["results"]},
    )


def summarize(experiment: str, arm: str, examples: list[ScoredExample]) -> ExperimentSummary:
    case_types = {f"case_type={example.case_type}" for example in examples}
    sources = {f"source={example.source}" for example in examples}
    slice_names = sorted(case_types | sources)
    return ExperimentSummary(
        experiment=experiment,
        arm=arm,
        overall=_metrics(examples),
        slices=[
            SliceSummary(name=name, metrics=_metrics([example for example in examples if _in_slice(example, name)]))
            for name in slice_names
        ],
    )


def format_summary(summary: ExperimentSummary) -> str:
    source_slices = [item for item in summary.slices if item.name.startswith("source=")]
    header = "metric".ljust(METRIC_WIDTH) + "".join(
        name.ljust(COLUMN_WIDTH) for name in ["overall", *[item.name for item in source_slices]]
    )
    rows = [
        (
            metric.key.ljust(METRIC_WIDTH)
            + _cell(metric)
            + "".join(_cell(_find(item.metrics, metric.key)) for item in source_slices)
        ).rstrip()
        for metric in summary.overall
    ]
    return "\n".join([f"experiment: {summary.experiment} (arm: {summary.arm})", header.rstrip(), *rows])


def _metrics(examples: list[ScoredExample]) -> list[MetricSummary]:
    keys = sorted({key for example in examples for key in example.scores})
    return [_metric(key, [example.scores[key] for example in examples if key in example.scores]) for key in keys]


def _metric(key: str, scores: list[float | None]) -> MetricSummary:
    applicable = [score for score in scores if score is not None]
    return MetricSummary(
        key=key,
        mean=sum(applicable) / len(applicable) if applicable else None,
        scored=len(applicable),
        not_applicable=len(scores) - len(applicable),
    )


def _in_slice(example: ScoredExample, name: str) -> bool:
    dimension, value = name.split("=")
    attribute: Callable[[ScoredExample], str] = {
        "source": lambda item: item.source,
        "case_type": lambda item: item.case_type,
    }[dimension]
    return attribute(example) == value


def _find(metrics: list[MetricSummary], key: str) -> MetricSummary:
    return next(metric for metric in metrics if metric.key == key)


def _cell(metric: MetricSummary) -> str:
    match metric.mean:
        case None:
            return "-".ljust(COLUMN_WIDTH)
        case mean:
            return f"{mean:.2f} ({metric.scored})".ljust(COLUMN_WIDTH)
