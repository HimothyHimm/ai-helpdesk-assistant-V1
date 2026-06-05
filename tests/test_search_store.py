"""
Tests for the Azure AI Search store.

These run with NO Search credentials and NO network, so CI stays green. They
verify graceful degradation: when Search isn't configured, the store reports
unavailable, search returns [], and index/upload raise a clear error instead
of crashing the app.
"""

from helpdesk.knowledge.search_store import SearchStore


def test_store_unavailable_without_config(monkeypatch):
    monkeypatch.setattr(
        "config.settings.azure_search_configured", lambda: False
    )
    store = SearchStore()
    assert store.available is False


def test_search_returns_empty_when_unavailable(monkeypatch):
    monkeypatch.setattr(
        "config.settings.azure_search_configured", lambda: False
    )
    store = SearchStore()
    assert store.search([0.1, 0.2, 0.3]) == []
    # An empty query vector also yields no results.
    assert store.search([]) == []


def test_ensure_index_errors_when_unavailable(monkeypatch):
    monkeypatch.setattr(
        "config.settings.azure_search_configured", lambda: False
    )
    store = SearchStore()
    try:
        store.ensure_index()
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "not configured" in str(exc)
