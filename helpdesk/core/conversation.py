"""Optional helper: encapsulates one troubleshooting session's message history.

The CLI manages its own history, so this class is NOT required to run the app.
It's here as a convenience for later: when you add a web API, you can create one
Conversation per user session instead of repeating the history bookkeeping.

It is written against the real LLMClient.reply() API. Note that reply() never
raises for AI errors — it returns a friendly string — so there is no exception
handling to do here.
"""

from helpdesk.core.llm_client import LLMClient
from helpdesk.core.prompts import build_troubleshooting_prompt


class Conversation:
    def __init__(self, client: LLMClient | None = None):
        self.client = client or LLMClient()
        self.history: list[dict] = []

    def send(self, user_message: str, faq_context: str | None = None) -> str:
        """Add the user's message, get the AI's reply, remember both, return it."""
        content = build_troubleshooting_prompt(user_message, faq_context)
        self.history.append({"role": "user", "content": content})
        reply = self.client.reply(self.history)
        self.history.append({"role": "assistant", "content": reply})
        return reply
