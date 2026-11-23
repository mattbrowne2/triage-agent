from uuid import UUID

from langsmith.evaluation import EvaluationResult
from langsmith.schemas import Example

from evals.models import ExperimentSummary, MetricSummary, ScoredExample, SliceSummary
from evals.summary import format_summary, scored_example, summarize


SCORED = [
    ScoredExample(
        case_id="human-correct", source="human", case_type="correct", scores={"root_cause_correct": 1, "cited": None}
    ),
    ScoredExample(
        case_id="human-vague", source="human", case_type="vague", scores={"root_cause_correct": 0, "cited": None}
    ),
    ScoredExample(
        case_id="monitor-checkout", source="monitor", case_type="correct", scores={"root_cause_correct": 1, "cited": 1}
    ),
]


def test_scored_example_reads_slice_metadata_and_scores_from_a_langsmith_row() -> None:
    example = Example(
        id=UUID(int=1),
        dataset_id=UUID(int=2),
        inputs={"alert": "ALR-8812", "as_of": "2026-11-17T02:15:00Z"},
        metadata={"case_id": "human-correct", "source": "human", "case_type": "correct"},
    )
    results = [EvaluationResult(key="report_produced", score=1), EvaluationResult(key="cited", score=None)]

    row = {"run": None, "example": example, "evaluation_results": {"results": results}}

    assert scored_example(row) == ScoredExample(
        case_id="human-correct", source="human", case_type="correct", scores={"report_produced": 1, "cited": None}
    )


def test_summarize_averages_applicable_scores_overall_and_per_slice() -> None:
    summary = summarize("triage-rag-1a2b", "rag", SCORED)

    assert summary == ExperimentSummary(
        experiment="triage-rag-1a2b",
        arm="rag",
        overall=[
            MetricSummary(key="cited", mean=1.0, scored=1, not_applicable=2),
            MetricSummary(key="root_cause_correct", mean=2 / 3, scored=3, not_applicable=0),
        ],
        slices=[
            SliceSummary(
                name="case_type=correct",
                metrics=[
                    MetricSummary(key="cited", mean=1.0, scored=1, not_applicable=1),
                    MetricSummary(key="root_cause_correct", mean=1.0, scored=2, not_applicable=0),
                ],
            ),
            SliceSummary(
                name="case_type=vague",
                metrics=[
                    MetricSummary(key="cited", mean=None, scored=0, not_applicable=1),
                    MetricSummary(key="root_cause_correct", mean=0.0, scored=1, not_applicable=0),
                ],
            ),
            SliceSummary(
                name="source=human",
                metrics=[
                    MetricSummary(key="cited", mean=None, scored=0, not_applicable=2),
                    MetricSummary(key="root_cause_correct", mean=0.5, scored=2, not_applicable=0),
                ],
            ),
            SliceSummary(
                name="source=monitor",
                metrics=[
                    MetricSummary(key="cited", mean=1.0, scored=1, not_applicable=0),
                    MetricSummary(key="root_cause_correct", mean=1.0, scored=1, not_applicable=0),
                ],
            ),
        ],
    )


def test_format_summary_shows_overall_and_alert_source_columns() -> None:
    assert format_summary(summarize("triage-rag-1a2b", "rag", SCORED)) == (
        "experiment: triage-rag-1a2b (arm: rag)\n"
        "metric                          overall      source=human source=monitor\n"
        "cited                           1.00 (1)     -            1.00 (1)\n"
        "root_cause_correct              0.67 (3)     0.50 (2)     1.00 (1)"
    )
