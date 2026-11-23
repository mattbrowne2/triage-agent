from incident_triage.incident_store.embeddings import build_embeddings
from incident_triage.settings import Settings


def test_embeddings_use_configured_openai_model_and_key() -> None:
    embeddings = build_embeddings(Settings(EMBEDDING_MODEL="text-embedding-3-small"))

    assert (embeddings.model, embeddings.openai_api_key.get_secret_value()) == (
        "text-embedding-3-small",
        "test-openai-key",
    )
