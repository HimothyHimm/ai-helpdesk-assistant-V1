"""Look up answers from your own IT documentation (the FAQ).

Two-tier search:
  1. PRIMARY  - semantic (vector) search via Azure AI Search. Embeds the user's
                question, finds the closest FAQ by MEANING, and returns it even
                when the wording doesn't match. This is the "RAG" retrieval step.
  2. FALLBACK - the original keyword match. Used automatically when Azure AI
                Search isn't configured/reachable, so the app still works offline.

Public signature is unchanged: KnowledgeBase().search(query) -> FaqEntry | None,
so nothing else in the app needs to change.
"""

import json
from dataclasses import dataclass

from config import settings


@dataclass
class FaqEntry:
    id: str
    question: str
    keywords: list[str]
    answer: str
    category: str = ""


class KnowledgeBase:
    """Loads FAQ entries and finds the best match for a question."""

    def __init__(self, faq_path=None):
        self.faq_path = faq_path or settings.FAQ_PATH
        self.entries: list[FaqEntry] = self._load()
        self._by_id = {e.id: e for e in self.entries}
        self._embedder = None
        self._store = None

    def _load(self) -> list[FaqEntry]:
        with open(self.faq_path, encoding="utf-8") as f:
            raw = json.load(f)
        return [FaqEntry(**item) for item in raw]

    def _ensure_search(self) -> bool:
        """Build the embedder + search store once. Return True if both ready."""
        if self._store is not None and self._embedder is not None:
            return self._store.available and self._embedder.available
        try:
            from helpdesk.knowledge.embedder import Embedder
            from helpdesk.knowledge.search_store import SearchStore

            self._embedder = Embedder()
            self._store = SearchStore()
        except Exception:
            return False
        return self._store.available and self._embedder.available

    def search(self, query: str) -> "FaqEntry | None":
        """Return the best-matching FAQ entry, or None if nothing is relevant.

        Tries semantic (vector) search first; falls back to keyword matching.
        """
        if self._ensure_search():
            try:
                vector = self._embedder.embed_query(query)
                hits = self._store.search(vector, top=1)
                if hits:
                    hit = hits[0]
                    score = hit.get("_score") or 0
                    if score >= settings.KB_SIMILARITY_THRESHOLD:
                        entry = self._by_id.get(hit.get("id"))
                        if entry:
                            return entry
                return None
            except Exception:
                pass
        return self._keyword_search(query)

    def _keyword_search(self, query: str) -> "FaqEntry | None":
        text = query.lower()
        best_entry = None
        best_score = 0
        for entry in self.entries:
            score = sum(1 for keyword in entry.keywords if keyword in text)
            if score > best_score:
                best_score = score
                best_entry = entry
        return best_entry  # None if no keyword matched