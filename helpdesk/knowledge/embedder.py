"""
Embedder for semantic FAQ search.

Backed by Azure OpenAI embeddings (deployment: text-embedding-3-small).
Turns text into vectors (lists of floats) so the knowledge base can match
questions by meaning rather than exact keywords.

Design notes
------------
- Same public interface as the Voyage version: `embed_documents(texts)` and
  `embed_query(text)`. The knowledge base depends only on these, so swapping
  Voyage -> Azure OpenAI required no change there.
- `available` reports whether real embeddings can be produced. When Azure
  isn't configured, the knowledge base falls back to keyword search.
- text-embedding-3-small returns L2-normalized vectors, so cosine similarity
  and dot product are equivalent -- the knowledge base can compare with a
  simple dot product, no extra math library needed.
"""

from __future__ import annotations

from typing import List

from config import settings


class Embedder:
    """Thin wrapper around Azure OpenAI embeddings."""

    def __init__(self) -> None:
        self._client = None
        self._available = False
        self._setup()

    def _setup(self) -> None:
        if not settings.azure_openai_configured():
            return
        try:
            from openai import AzureOpenAI
        except ImportError:
            return
        try:
            self._client = AzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
            )
            self._available = True
        except Exception:  # pragma: no cover - defensive
            self._available = False

    @property
    def available(self) -> bool:
        """True when real embeddings can be produced."""
        return self._available

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of FAQ entries (the stored documents)."""
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        """Embed a single user query. Returns one vector."""
        vectors = self._embed([text])
        return vectors[0] if vectors else []

    def _embed(self, texts: List[str]) -> List[List[float]]:
        if not self._available or not texts:
            return []
        try:
            response = self._client.embeddings.create(
                model=settings.AZURE_OPENAI_EMBED_DEPLOYMENT,  # deployment name
                input=texts,
            )
            # Results come back in the same order as the input texts.
            return [item.embedding for item in response.data]
        except Exception:
            # On any failure, signal "no embeddings" so the KB falls back
            # to keyword search instead of crashing.
            return []
