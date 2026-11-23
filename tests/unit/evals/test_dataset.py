from collections.abc import Callable
from typing import Any

from langsmith.schemas import ExampleCreate

from evals.dataset import dataset_name, ensure_dataset, to_examples
from evals.models import EvalCase, EvalSuite


def test_dataset_name_changes_with_the_cases_file_content() -> None:
    assert dataset_name('{"cases": []}') == "incident-triage-evals-4fb3f1e0"


def test_examples_carry_inputs_expected_outcome_and_slice_metadata(human_correct_case: EvalCase) -> None:
    examples = to_examples(EvalSuite(cases=[human_correct_case]))

    assert [example.model_dump(exclude={"created_at"}) for example in examples] == [
        ExampleCreate(
            inputs={
                "alert": "ALR-8812: checkout-service 5xx error rate 18% (threshold 5%) since 2026-11-17T02:09:00Z",
                "as_of": "2026-11-17T02:15:00Z",
            },
            reference_outputs=human_correct_case.expected.model_dump(mode="json"),
            metadata={"case_id": "human-correct", "source": "human", "case_type": "correct"},
        ).model_dump(exclude={"created_at"})
    ]


def test_ensure_dataset_uploads_cases_only_when_the_dataset_is_missing(
    langsmith_client_factory: Callable[..., Any], human_correct_case: EvalCase
) -> None:
    suite = EvalSuite(cases=[human_correct_case])
    missing = langsmith_client_factory(existing=set())
    present = langsmith_client_factory(existing={"incident-triage-evals-test"})

    ensure_dataset(missing, suite, "incident-triage-evals-test")
    ensure_dataset(present, suite, "incident-triage-evals-test")

    assert (
        [(dataset_id, [example.inputs for example in examples]) for dataset_id, examples in missing.uploads],
        present.uploads,
    ) == (
        [("incident-triage-evals-test", [example.inputs for example in to_examples(suite)])],
        [],
    )
