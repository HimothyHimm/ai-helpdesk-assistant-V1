"""Categorize an incident into a Category and Priority.

Two-tier categorization:
  1. PRIMARY  - an LLM classifier (Azure OpenAI) reads the request and picks a
                category + priority by MEANING, constrained to the enums below.
  2. FALLBACK - the original keyword rules, used automatically when the LLM is
                unavailable or returns something unusable. Fully offline and
                explainable.

Public signature is unchanged: categorize(description) -> Incident. The rule
logic is also exposed as rule_categorize() for deterministic, offline testing.
"""

from helpdesk.incidents.models import Category, Incident, Priority

# Keyword -> Category. Checked top to bottom; FIRST match wins. Order matters:
# SECURITY is first so "phishing email" is caught as security, not email.
_CATEGORY_KEYWORDS: dict[Category, list[str]] = {
    Category.SECURITY: ["phishing", "virus", "malware", "hacked", "breach", "suspicious"],
    Category.ACCESS: ["password", "login", "log in", "locked out", "reset", "mfa", "permission", "access"],
    Category.NETWORK: ["wifi", "wi-fi", "internet", "vpn", "network", "connection", "dns", "slow"],
    Category.EMAIL: ["email", "outlook", "inbox", "mailbox", "smtp", "spam"],
    Category.HARDWARE: ["printer", "laptop", "monitor", "keyboard", "mouse", "screen", "battery", "won't turn on"],
    Category.SOFTWARE: ["install", "application", "app", "crash", "error", "update", "license", "excel", "word"],
}

# Words that bump the priority up.
_HIGH_PRIORITY_WORDS = ["urgent", "asap", "immediately", "can't work", "cannot work", "production"]
_CRITICAL_WORDS = ["outage", "down", "everyone", "company-wide", "breach", "ransomware"]

_llm = None  # lazily-created shared LLM client


def _get_llm():
    """Create the LLM client once, on first use (no import-time side effects)."""
    global _llm
    if _llm is None:
        from helpdesk.core.llm_client import LLMClient
        _llm = LLMClient()
    return _llm


def categorize(description: str) -> Incident:
    """Turn a free-text request into a structured Incident.

    Tries the LLM classifier first; falls back to keyword rules on any failure.
    """
    incident = _llm_categorize(description)
    if incident is not None:
        return incident
    return rule_categorize(description)


def _llm_categorize(description: str) -> "Incident | None":
    """Classify via the LLM and map the result back to the enums. None if unusable."""
    try:
        result = _get_llm().classify(
            description,
            categories=[c.value for c in Category],
            priorities=[p.value for p in Priority],
        )
    except Exception:
        return None
    if not result:
        return None
    try:
        category = Category(result["category"])
        priority = Priority(result["priority"])
    except (ValueError, KeyError):
        return None
    return Incident(description=description, category=category, priority=priority)


def rule_categorize(description: str) -> Incident:
    """Keyword-based categorization. Deterministic, offline, explainable."""
    text = description.lower()
    category = _detect_category(text)
    priority = _detect_priority(text, category)
    return Incident(description=description, category=category, priority=priority)


def _detect_category(text: str) -> Category:
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return Category.OTHER


def _detect_priority(text: str, category: Category) -> Priority:
    if any(word in text for word in _CRITICAL_WORDS):
        return Priority.CRITICAL
    if category is Category.SECURITY:
        return Priority.HIGH
    if any(word in text for word in _HIGH_PRIORITY_WORDS):
        return Priority.HIGH
    return Priority.MEDIUM