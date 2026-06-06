"""
LLM client for the AI help desk assistant.

Backed by Azure OpenAI. The client is intentionally STATELESS: it does not
store conversation history. The caller (e.g. the CLI) owns the running
history list and passes the full conversation on every call, because the
model has no memory between requests.

Design notes
------------
- Same public interface as earlier steps: `LLMClient.reply(history)`.
  Swapping the provider (Anthropic -> Azure OpenAI) did not change the
  shape the rest of the app depends on, so the CLI needs no changes.
- `classify()` adds LLM-assisted incident categorization, reusing the same
  client. It returns plain dict/None so the categorizer can fall back to rules.
- Graceful degradation: if Azure isn't configured (no key/endpoint) or the
  `openai` package isn't installed, calls return a friendly message / None
  instead of raising, so the categorizer and FAQ search keep working offline.
"""

from __future__ import annotations

import json
from typing import List, Dict

from config import settings

# The system prompt that gives the assistant its help-desk persona.
SYSTEM_PROMPT = (
    "You are an enterprise IT help desk assistant. You support employees with "
    "Microsoft 365, Intune / device management, identity and access (Entra ID), "
    "VPN and networking, and endpoint / hardware issues. "
    "Troubleshoot step by step, ask one clarifying question at a time when needed, "
    "and keep answers concise and practical. If an issue involves a possible "
    "security incident (e.g. suspected phishing, account compromise), advise the "
    "user to escalate to the security team rather than resolving it themselves."
)

# Message returned when the AI provider isn't available. Keeps the app usable.
_OFFLINE_NOTICE = (
    "[AI not configured] I can still categorize your request and search the "
    "knowledge base, but live AI troubleshooting needs an Azure OpenAI key and "
    "endpoint in your .env file."
)


class LLMClient:
    """Thin, stateless wrapper around the Azure OpenAI chat API."""

    def __init__(self) -> None:
        self._client = None
        self._enabled = False
        self._init_error: str | None = None
        self._setup()

    def _setup(self) -> None:
        """Create the Azure OpenAI client, degrading gracefully on any problem."""
        if not settings.azure_openai_configured():
            return

        try:
            from openai import AzureOpenAI
        except ImportError:
            self._init_error = (
                "The 'openai' package isn't installed. Run "
                "'pip install -r requirements.txt'."
            )
            return

        try:
            self._client = AzureOpenAI(
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
            )
            self._enabled = True
        except Exception as exc:  # pragma: no cover - defensive
            self._init_error = f"Could not initialize Azure OpenAI client: {exc}"

    @property
    def enabled(self) -> bool:
        """True when a live Azure OpenAI call can be made."""
        return self._enabled

    def reply(self, history: List[Dict[str, str]]) -> str:
        """Return the assistant's next message given the full conversation so far."""
        if not self._enabled:
            return self._init_error or _OFFLINE_NOTICE

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        try:
            from openai import APIConnectionError, RateLimitError, APIStatusError
        except ImportError:  # pragma: no cover
            return _OFFLINE_NOTICE

        try:
            response = self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=messages,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
            )
            return response.choices[0].message.content or ""
        except APIConnectionError:
            return (
                "I couldn't reach the AI service (network issue). Please check "
                "your connection and try again."
            )
        except RateLimitError:
            return (
                "The AI service is rate-limited right now. Wait a moment and "
                "try again."
            )
        except APIStatusError as exc:
            return f"The AI service returned an error (status {exc.status_code}). Try again shortly."
        except Exception as exc:  # pragma: no cover
            return f"Unexpected error talking to the AI service: {exc}"

    def classify(self, text: str, categories: List[str], priorities: List[str]) -> "Dict[str, str] | None":
        """
        Classify `text` into one of `categories` and one of `priorities`.

        Returns {"category": <value>, "priority": <value>} drawn from the given
        lists, or None if the LLM is unavailable or its output is unusable - so
        the caller can fall back to rules. Temperature 0 for repeatable results.
        """
        if not self._enabled:
            return None

        system = (
            "You classify enterprise IT help desk requests. "
            f"Pick exactly one category from: {', '.join(categories)}. "
            f"Pick exactly one priority from: {', '.join(priorities)}. "
            "Reply with ONLY a JSON object like "
            '{"category": "<category>", "priority": "<priority>"} and nothing else.'
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ]

        try:
            response = self._client.chat.completions.create(
                model=settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=messages,
                max_tokens=50,
                temperature=0,
            )
            raw = (response.choices[0].message.content or "").strip()
        except Exception:
            return None

        if "{" in raw and "}" in raw:
            raw = raw[raw.index("{"): raw.rindex("}") + 1]
        try:
            data = json.loads(raw)
        except Exception:
            return None

        category = str(data.get("category", "")).strip().lower()
        priority = str(data.get("priority", "")).strip().lower()
        if category in categories and priority in priorities:
            return {"category": category, "priority": priority}
        return None