"""Look up answers from your own IT documentation (the FAQ).

VERSION 1 (this file): loads a JSON file and does simple keyword matching.
It works offline and is easy to understand. In Step 3 we replace the matching
logic with semantic (vector) search so it finds answers even when the user's
wording doesn't exactly match — this is the "RAG" pattern. The public function
signatures stay the same, so the rest of the app won't need to change.
"""

import json
from dataclasses import dataclass

from config import settings


@dataclass
class FaqEntry:
    question: str
    keywords: list[str]
    answer: str


class KnowledgeBase:
    """Loads FAQ entries and finds the best match for a question."""

    def __init__(self, faq_path=None):
        self.faq_path = faq_path or settings.FAQ_PATH
        self.entries: list[FaqEntry] = self._load()

    def _load(self) -> list[FaqEntry]:
        with open(self.faq_path, encoding="utf-8") as f:
            raw = json.load(f)
        return [FaqEntry(**item) for item in raw]

    def search(self, query: str) -> FaqEntry | None:
        """Return the best-matching FAQ entry, or None if nothing is relevant."""
        text = query.lower()
        best_entry = None
        best_score = 0

        for entry in self.entries:
            score = sum(1 for keyword in entry.keywords if keyword in text)
            if score > best_score:
                best_score = score
                best_entry = entry

        return best_entry  # None if no keyword matched
