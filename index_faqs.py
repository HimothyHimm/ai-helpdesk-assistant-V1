"""
One-time (re-runnable) script to load your FAQ data into Azure AI Search.

What it does:
  1. Reads your FAQ file (config.settings.FAQ_PATH).
  2. Embeds each FAQ question with Azure OpenAI (text-embedding-3-small).
  3. Creates the vector index if needed, then uploads the entries.

Run it:
    python index_faqs.py

Re-run it any time you change faq.json. It's safe to run repeatedly --
uploading a document with an existing id just overwrites it.

Requires AZURE_OPENAI_* and AZURE_SEARCH_* values in your .env.
"""

from __future__ import annotations

import json
import sys

from config import settings
from helpdesk.knowledge.embedder import Embedder
from helpdesk.knowledge.search_store import SearchStore


def _load_faqs(path: str):
    """Read the FAQ file and normalize each entry to a common shape."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    # Accept either a top-level list, or a dict wrapping a list under a key.
    if isinstance(data, dict):
        for key in ("faqs", "items", "entries", "data"):
            if isinstance(data.get(key), list):
                data = data[key]
                break

    if not isinstance(data, list):
        raise ValueError(
            "Couldn't find a list of FAQ entries in the file. Expected a JSON "
            "list, or a dict containing one under 'faqs'/'items'/'entries'/'data'."
        )

    entries = []
    for i, item in enumerate(data):
        # Be tolerant of common field-name variations.
        question = (
            item.get("question")
            or item.get("q")
            or item.get("title")
            or ""
        )
        answer = (
            item.get("answer")
            or item.get("a")
            or item.get("response")
            or item.get("content")
            or ""
        )
        entry_id = str(item.get("id", i + 1))
        category = item.get("category", "") or ""
        if not question:
            continue
        entries.append(
            {
                "id": entry_id,
                "question": question,
                "answer": answer,
                "category": category,
            }
        )
    return entries


def main() -> int:
    # Preflight checks with clear, friendly errors.
    if not settings.azure_openai_configured():
        print(
            "Azure OpenAI isn't configured. Add AZURE_OPENAI_ENDPOINT and "
            "AZURE_OPENAI_API_KEY to your .env, then re-run."
        )
        return 1
    if not settings.azure_search_configured():
        print(
            "Azure AI Search isn't configured. Add AZURE_SEARCH_ENDPOINT and "
            "AZURE_SEARCH_API_KEY to your .env, then re-run."
        )
        return 1

    embedder = Embedder()
    if not embedder.available:
        print("Embedder unavailable (check Azure OpenAI config / openai package).")
        return 1

    store = SearchStore()
    if not store.available:
        print(
            "Search store unavailable. Check the azure-search-documents package "
            "and your AZURE_SEARCH_* values."
        )
        return 1

    print(f"Reading FAQs from: {settings.FAQ_PATH}")
    entries = _load_faqs(settings.FAQ_PATH)
    print(f"Found {len(entries)} FAQ entries.")
    if not entries:
        print("Nothing to index.")
        return 0

    print("Embedding questions...")
    questions = [e["question"] for e in entries]
    vectors = embedder.embed_documents(questions)
    if len(vectors) != len(entries):
        print(
            f"Embedding count ({len(vectors)}) didn't match entry count "
            f"({len(entries)}). Aborting to avoid a misaligned index."
        )
        return 1
    for entry, vec in zip(entries, vectors):
        entry["embedding"] = vec

    print("Ensuring the search index exists...")
    store.ensure_index()

    print("Uploading entries to Azure AI Search...")
    uploaded = store.upload(entries)
    print(f"Done. Uploaded {uploaded} entries to index '{settings.AZURE_SEARCH_INDEX}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
