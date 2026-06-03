"""Tests for the LLM client that DON'T require a network or API key.

We can't unit-test a real API call here (that needs a live key and network),
but we CAN verify the safety nets: when the AI isn't configured, the client
returns a friendly message instead of crashing.
"""

from config import settings
from helpdesk.core.llm_client import LLMClient
from helpdesk.core.prompts import build_troubleshooting_prompt


def test_reply_without_api_key_returns_friendly_message(monkeypatch):
    # Force the "no key configured" state regardless of the dev's environment.
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")

    client = LLMClient()
    result = client.reply([{"role": "user", "content": "my printer is broken"}])

    assert result.startswith("[AI not configured]")


def test_prompt_includes_faq_context_when_provided():
    prompt = build_troubleshooting_prompt(
        "how do I reset my password?",
        faq_context="Use the self-service portal.",
    )
    assert "self-service portal" in prompt
    assert "how do I reset my password?" in prompt


def test_prompt_is_just_the_message_without_context():
    prompt = build_troubleshooting_prompt("hello")
    assert prompt == "hello"
