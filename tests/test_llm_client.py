"""
Tests for the Azure OpenAI LLM client.

These run with NO API key and NO network, so CI stays green. They verify the
graceful-degradation path: when Azure isn't configured, the client reports
disabled and returns a friendly notice instead of crashing.
"""

from helpdesk.core.llm_client import LLMClient, _OFFLINE_NOTICE


def test_client_disabled_without_config(monkeypatch):
    # Force "not configured" regardless of the environment running the tests.
    monkeypatch.setattr(
        "config.settings.azure_openai_configured", lambda: False
    )
    client = LLMClient()
    assert client.enabled is False


def test_reply_returns_friendly_notice_offline(monkeypatch):
    monkeypatch.setattr(
        "config.settings.azure_openai_configured", lambda: False
    )
    client = LLMClient()
    out = client.reply([{"role": "user", "content": "my VPN won't connect"}])
    # Either the offline notice or an init-error string -- never a crash,
    # and never an empty response.
    assert isinstance(out, str) and out
    assert out.startswith("[AI not configured]") or "openai" in out.lower()
