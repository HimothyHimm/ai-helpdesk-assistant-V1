"""Categorize an incident into a Category and Priority.

VERSION 1 (this file): simple keyword rules. No AI, no API key, fully testable.
This is deliberate — your domain knowledge is encoded as plain rules first, so
you have a working, explainable baseline. In Step 4 we add an LLM-powered
categorizer that falls back to these rules when the AI is unavailable.
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


def categorize(description: str) -> Incident:
    """Turn a free-text request into a structured Incident."""
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
