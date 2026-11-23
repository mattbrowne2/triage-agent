from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore

from incident_triage.incident_store.documents import incident_document
from incident_triage.models.incident import IncidentArchive, PastIncident
from incident_triage.models.incident_search import IncidentMatch, IncidentSearchQuery, IncidentSearchResponse


class IncidentIndex:
    def __init__(self, incidents: list[PastIncident], embeddings: Embeddings, min_similarity: float) -> None:
        self._incidents = {incident.key: incident for incident in incidents}
        self._min_similarity = min_similarity
        self._store = InMemoryVectorStore(embeddings)
        self._store.add_documents(
            [
                Document(page_content=incident_document(incident), metadata={"key": incident.key})
                for incident in incidents
            ]
        )

    @classmethod
    def from_file(cls, path: Path, embeddings: Embeddings, min_similarity: float) -> "IncidentIndex":
        return cls(IncidentArchive.model_validate_json(path.read_text()).incidents, embeddings, min_similarity)

    def search(self, query: IncidentSearchQuery) -> IncidentSearchResponse:
        scored = self._store.similarity_search_with_score(query.query, k=query.limit)
        return IncidentSearchResponse(
            matches=[
                IncidentMatch(similarity=round(score, 3), incident=self._incidents[document.metadata["key"]])
                for document, score in scored
                if score >= self._min_similarity
            ]
        )
