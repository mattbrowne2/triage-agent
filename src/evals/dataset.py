from hashlib import sha256

from langsmith import Client
from langsmith.schemas import ExampleCreate

from evals.cases import case_input
from evals.models import CaseMetadata, EvalSuite


DATASET_PREFIX = "incident-triage-evals"


def dataset_name(suite_json: str) -> str:
    return f"{DATASET_PREFIX}-{sha256(suite_json.encode()).hexdigest()[:8]}"


def to_examples(suite: EvalSuite) -> list[ExampleCreate]:
    return [
        ExampleCreate(
            inputs=case_input(case).model_dump(mode="json"),
            reference_outputs=case.expected.model_dump(mode="json"),
            metadata=CaseMetadata(case_id=case.id, source=case.source, case_type=case.case_type).model_dump(
                mode="json"
            ),
        )
        for case in suite.cases
    ]


def ensure_dataset(client: Client, suite: EvalSuite, name: str) -> None:
    if client.has_dataset(dataset_name=name):
        return
    dataset = client.create_dataset(name, description="Incident triage cases with expected outcomes")
    client.create_examples(dataset_id=dataset.id, examples=to_examples(suite))
