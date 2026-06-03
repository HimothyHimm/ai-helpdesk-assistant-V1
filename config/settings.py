"""Central place for configuration and secrets.

Every other module imports settings from here instead of reading os.environ
directly. That way there is ONE place to look when something is misconfigured.
"""

import os
from pathlib import Path

# Load variables from a local .env file into the environment (if present).
# We import optionally so the app still runs before dependencies are installed.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Project root, computed from this file's location. Handy for building paths
# to data files without hardcoding absolute paths.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# --- AI model settings (used from Step 2 onward) ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")

# --- ServiceNow settings (used later) ---
SERVICENOW_INSTANCE_URL = os.getenv("SERVICENOW_INSTANCE_URL", "")
SERVICENOW_USERNAME = os.getenv("SERVICENOW_USERNAME", "")
SERVICENOW_PASSWORD = os.getenv("SERVICENOW_PASSWORD", "")

# --- Knowledge base ---
FAQ_PATH = PROJECT_ROOT / "helpdesk" / "knowledge" / "data" / "faq.json"


def ai_is_configured() -> bool:
    """True if we have what we need to call the AI model."""
    return bool(ANTHROPIC_API_KEY)
