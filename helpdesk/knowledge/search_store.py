"""
Azure AI Search vector store for the help desk knowledge base.

This is the "vector database" layer of the RAG pipeline. It stores each FAQ
entry along with its embedding vector, and answers a user's question by
finding the FAQ whose vector is closest in MEANING (cosine similarity), not
by matching keywords.

Pieces
------
- ensure_index():   create the index (schema) if it doesn't exist yet.
- upload(entries):  push FAQ entries (each with a precomputed embedding).
- search(vector):   vector query -> best-matching FAQ entries with scores.

Design notes
------------
- Graceful degradation: if Azure AI Search isn't configured, or the SDK isn't
  installed, `available` is False and the caller falls back to the existing
  keyword/in-memory path. The app never crashes just because Search is absent.
- Auth uses the Search ADMIN key for simplicity (one key for create + upload +
  query). A production system would use a read-only query key at runtime.
- The vector field declares EMBED_DIMENSIONS dimensions (1536 for
  text-embedding-3-small) and a cosine HNSW profile -- the standard, recommended
  vector-search setup.
"""

from __future__ import annotations

from typing import List, Dict, Any

from config import settings


class SearchStore:
    """Thin wrapper around an Azure AI Search index used as a vector store."""

    def __init__(self) -> None:
        self._index_client = None
        self._search_client = None
        self._available = False
        self._setup()

    def _setup(self) -> None:
        if not settings.azure_search_configured():
            return
        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents import SearchClient
            from azure.search.documents.indexes import SearchIndexClient
        except ImportError:
            return
        try:
            cred = AzureKeyCredential(settings.AZURE_SEARCH_API_KEY)
            self._index_client = SearchIndexClient(
                endpoint=settings.AZURE_SEARCH_ENDPOINT, credential=cred
            )
            self._search_client = SearchClient(
                endpoint=settings.AZURE_SEARCH_ENDPOINT,
                index_name=settings.AZURE_SEARCH_INDEX,
                credential=cred,
            )
            self._available = True
        except Exception:  # pragma: no cover - defensive
            self._available = False

    @property
    def available(self) -> bool:
        """True when Azure AI Search can be used."""
        return self._available

    def ensure_index(self) -> None:
        """
        Create the vector index if it doesn't already exist.

        The schema:
          - id      (key)        : unique FAQ id
          - question (searchable): the FAQ question text
          - answer   (retrievable): the FAQ answer text
          - category (filterable): optional category tag
          - embedding (vector)   : the question's embedding vector
        """
        if not self._available:
            raise RuntimeError("Azure AI Search is not configured.")

        from azure.search.documents.indexes.models import (
            SearchIndex,
            SimpleField,
            SearchableField,
            SearchField,
            SearchFieldDataType,
            VectorSearch,
            HnswAlgorithmConfiguration,
            HnswParameters,
            VectorSearchProfile,
        )

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="hnsw-config",
                    parameters=HnswParameters(
                        m=4,
                        ef_construction=400,
                        ef_search=500,
                        metric="cosine",
                    ),
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="vector-profile",
                    algorithm_configuration_name="hnsw-config",
                )
            ],
        )

        fields = [
            SimpleField(
                name="id", type=SearchFieldDataType.String, key=True
            ),
            SearchableField(name="question", type=SearchFieldDataType.String),
            SearchableField(
                name="answer",
                type=SearchFieldDataType.String,
                searchable=False,
            ),
            SimpleField(
                name="category",
                type=SearchFieldDataType.String,
                filterable=True,
            ),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=settings.EMBED_DIMENSIONS,
                vector_search_profile_name="vector-profile",
            ),
        ]

        index = SearchIndex(
            name=settings.AZURE_SEARCH_INDEX,
            fields=fields,
            vector_search=vector_search,
        )
        # create_or_update is idempotent: safe to run repeatedly.
        self._index_client.create_or_update_index(index)

    def upload(self, entries: List[Dict[str, Any]]) -> int:
        """
        Upload FAQ entries to the index.

        Each entry must be a dict with: id, question, answer, category (optional),
        and embedding (a list of floats). Returns the count uploaded.
        """
        if not self._available:
            raise RuntimeError("Azure AI Search is not configured.")
        if not entries:
            return 0
        result = self._search_client.upload_documents(documents=entries)
        return len([r for r in result if getattr(r, "succeeded", True)])

    def search(self, query_vector: List[float], top: int = 3) -> List[Dict[str, Any]]:
        """
        Vector search: return the `top` FAQ entries closest in meaning to the
        query vector, each with a similarity score in `_score`.
        """
        if not self._available or not query_vector:
            return []

        from azure.search.documents.models import VectorizedQuery

        vq = VectorizedQuery(
            vector=query_vector,
            k_nearest_neighbors=top,
            fields="embedding",
        )
        try:
            results = self._search_client.search(
                search_text=None,
                vector_queries=[vq],
                select=["id", "question", "answer", "category"],
                top=top,
            )
            out: List[Dict[str, Any]] = []
            for r in results:
                out.append(
                    {
                        "id": r.get("id"),
                        "question": r.get("question"),
                        "answer": r.get("answer"),
                        "category": r.get("category"),
                        "_score": r.get("@search.score"),
                    }
                )
            return out
        except Exception:
            # On any query failure, return nothing so the caller can fall back.
            return []
