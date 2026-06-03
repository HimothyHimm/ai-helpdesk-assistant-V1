"""Tests for the rule-based categorizer.

Run all tests with:  pytest

Writing tests early is a habit worth building. Each test states an expected
behavior in plain terms, so when you change the rules later, these tell you
instantly whether you broke anything.
"""

from helpdesk.incidents.categorizer import categorize
from helpdesk.incidents.models import Category, Priority


def test_password_request_is_access():
    incident = categorize("I forgot my password and I'm locked out")
    assert incident.category == Category.ACCESS


def test_vpn_request_is_network():
    incident = categorize("My VPN won't connect from home")
    assert incident.category == Category.NETWORK


def test_outage_is_critical():
    incident = categorize("The whole network is down for everyone")
    assert incident.priority == Priority.CRITICAL


def test_security_issue_is_high_priority():
    incident = categorize("I think I clicked a phishing email")
    assert incident.category == Category.SECURITY
    assert incident.priority == Priority.HIGH


def test_unknown_request_falls_back_to_other():
    incident = categorize("Where is the office cafeteria?")
    assert incident.category == Category.OTHER
