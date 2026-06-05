"""
Central configuration for the AI help desk assistant.

All secrets and environment-specific values are read here from the .env file
(never hardcoded), so the rest of the code imports from `config.settings`
instead of touching os.environ directly. This is also why .env is git-ignored:
the project goes on a public profile and must never leak a key.
"""

from __future__ import annotations

import os

# Load .env if python-dotenv is available. If it isn't (or there's no .env),
# we just fall back to real environment variables / defaults -- no crash.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


def _get(name: str, default: str = "") -> str:
    """Read an env var, treating placeholder values as 'not set'."""
    value = os.environ.get(name, default).strip()
    # Common placeholders from .env.example shouldn't count as configured.
    if value.lower() in {"your-key-here", "your-endpoint-here", ""}:
        return ""
    return value


# --- Azure OpenAI (chat + embeddings) ---------------------------------------
# Endpoint looks like: https://YOUR-RESOURCE.openai.azure.com/
AZURE_OPENAI_ENDPOINT = _get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = _get("AZURE_OPENAI_API_KEY")

# Stable GA API version. Not a -preview, to keep the public repo on a
# supported, non-experimental API surface.
AZURE_OPENAI_API_VERSION = os.environ.get(
    "AZURE_OPENAI_API_VERSION", "2024-10-21"
).strip()

# IMPORTANT: these are the DEPLOYMENT names you chose in Azure AI Foundry,
# not the model names. They happen to match the model names here, which keeps
# things readable. Change them if your deployments are named differently.
AZURE_OPENAI_CHAT_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-4.1-mini"
).strip()
AZURE_OPENAI_EMBED_DEPLOYMENT = os.environ.get(
    "AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-small"
).strip()

# --- LLM generation tuning --------------------------------------------------
LLM_MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "1024"))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0.3"))

# --- Knowledge base / semantic search --------------------------------------
# Cosine-similarity cutoff: below this, a match is treated as "no good answer"
# and we don't surface a misleading FAQ entry.
KB_SIMILARITY_THRESHOLD = float(os.environ.get("KB_SIMILARITY_THRESHOLD", "0.35"))


def azure_openai_configured() -> bool:
    """True when both the Azure endpoint and key are present."""
    return bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY)

# --- Knowledge base FAQ file ---
# Path to the FAQ data, resolved relative to the project root so it works
# on any machine (not a hardcoded C:\Users\... path). This matters for a
# public repo someone might clone.
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
FAQ_PATH = str(_PROJECT_ROOT / "helpdesk" / "knowledge" / "data" / "faq.json")
