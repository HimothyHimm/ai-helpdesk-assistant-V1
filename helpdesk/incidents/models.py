"""Data models for incidents.

These are plain Python objects that describe an IT request in a structured way.
Using enums (instead of loose strings like "high") prevents typos and makes the
valid options obvious to anyone reading the code.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Category(str, Enum):
    """The buckets an incident can fall into. Tune these to match your org."""

    HARDWARE = "hardware"
    SOFTWARE = "software"
    NETWORK = "network"
    ACCESS = "access"          # passwords, logins, permissions
    EMAIL = "email"
    SECURITY = "security"
    OTHER = "other"


class Priority(str, Enum):
    """How urgent the incident is."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Incident:
    """A single support request, in structured form."""

    description: str
    category: Category = Category.OTHER
    priority: Priority = Priority.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)

    def summary(self) -> str:
        """A one-line human-readable summary."""
        return f"[{self.priority.value.upper()}] {self.category.value}: {self.description}"
