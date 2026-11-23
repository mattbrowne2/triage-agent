from pathlib import Path

from langchain_core.embeddings import DeterministicFakeEmbedding

from incident_triage.incident_store.documents import incident_document
from incident_triage.incident_store.index import IncidentIndex
from incident_triage.models.incident import PastIncident
from incident_triage.models.incident_search import IncidentMatch, IncidentSearchQuery, IncidentSearchResponse


SEED_INCIDENTS = Path(__file__).parents[4] / "data" / "incidents" / "past_incidents.json"


def test_search_returns_the_incident_whose_document_matches_the_query(
    incident_index: IncidentIndex, resolved_contract_incident: PastIncident
) -> None:
    response = incident_index.search(IncidentSearchQuery(query=incident_document(resolved_contract_incident)))

    assert response == IncidentSearchResponse(
        matches=[IncidentMatch(similarity=1.0, incident=resolved_contract_incident)]
    )


def test_search_drops_matches_below_the_minimum_similarity(incident_index: IncidentIndex) -> None:
    response = incident_index.search(IncidentSearchQuery(query="Kafka consumer lag in the billing pipeline"))

    assert response == IncidentSearchResponse(matches=[])


def test_search_returns_at_most_limit_matches_most_similar_first(
    resolved_contract_incident: PastIncident,
    open_load_balancer_incident: PastIncident,
    fake_embeddings: DeterministicFakeEmbedding,
) -> None:
    index = IncidentIndex([resolved_contract_incident, open_load_balancer_incident], fake_embeddings, min_similarity=-1)

    one = index.search(IncidentSearchQuery(query=incident_document(open_load_balancer_incident), limit=1))
    two = index.search(IncidentSearchQuery(query=incident_document(open_load_balancer_incident), limit=2))

    assert ([match.incident.key for match in one.matches], [match.incident.key for match in two.matches]) == (
        ["INC-316"],
        ["INC-316", "INC-311"],
    )


def test_index_loads_seed_incidents_from_file(fake_embeddings: DeterministicFakeEmbedding) -> None:
    index = IncidentIndex.from_file(SEED_INCIDENTS, fake_embeddings, min_similarity=0.5)
    inventory_noise_query = (
        "inventory-service timeout warnings to inventory-db\n"
        "Service: inventory-service\n"
        "Symptoms: inventory-service logged warnings: Timeout calling inventory-db after 2000ms, retry succeeded. "
        "About one per minute, around the clock. No customer-facing errors.\n"
        "Confirmed root cause: Known background noise: inventory-db's nightly vacuum and periodic connection "
        "recycling cause occasional slow first attempts. The client retries and every retry succeeds."
    )

    response = index.search(IncidentSearchQuery(query=inventory_noise_query))

    assert [match.incident.key for match in response.matches] == ["INC-287"]
