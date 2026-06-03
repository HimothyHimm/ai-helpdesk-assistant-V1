"""The client that talks to the AI model (Anthropic's Claude).

VERSION 2: real API calls. The class is intentionally STATELESS — it does not
remember the conversation. Memory lives wherever the client is used (the CLI
keeps a `history` list and passes it in every time). This matters because the
model itself has no memory between calls: you must resend the whole conversation
on every request. Keeping the client stateless also means it reuses cleanly when
we add a web API later, where each request manages its own history.

SDK shape (verified against https://docs.claude.com/en/api/overview):
    client = anthropic.Anthropic(api_key=...)
    msg = client.messages.create(model=, max_tokens=, system=, messages=[...])
    text = msg.content[0].text
"""

from config import settings
from helpdesk.core import prompts


class LLMClient:
    def __init__(self, model: str | None = None, max_tokens: int = 1024):
        self.model = model or settings.LLM_MODEL
        self.max_tokens = max_tokens

    def reply(self, history: list[dict]) -> str:
        """Send the full conversation `history` and return the assistant's text.

        `history` is a list of message dicts, e.g.
            [{"role": "user", "content": "my wifi is down"},
             {"role": "assistant", "content": "Have you tried..."},
             {"role": "user", "content": "yes, still nothing"}]

        Returns a friendly message (never raises) if the AI isn't usable yet, so
        the rest of the app keeps working offline.
        """
        # Graceful fallback #1: no API key configured.
        if not settings.ai_is_configured():
            return (
                "[AI not configured] Add ANTHROPIC_API_KEY to your .env file to "
                "enable live AI answers. (The categorizer and FAQ still work.)"
            )

        # Graceful fallback #2: SDK not installed yet.
        try:
            import anthropic
        except ImportError:
            return "[Missing dependency] Run:  pip install -r requirements.txt"

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=prompts.SYSTEM_PROMPT,
                messages=history,
            )
        except anthropic.APIConnectionError:
            return "[Connection error] Couldn't reach the AI service. Check your internet connection."
        except anthropic.RateLimitError:
            return "[Rate limited] Too many requests right now — wait a moment and try again."
        except anthropic.APIStatusError as e:
            return f"[API error {e.status_code}] The AI service returned an error. Check your API key and model name."

        return self._extract_text(response)

    @staticmethod
    def _extract_text(response) -> str:
        """Pull the text out of the response, ignoring any non-text blocks."""
        parts = [
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ]
        return "".join(parts) if parts else "(The AI returned no text.)"

    def ask_once(self, user_message: str, faq_context: str | None = None) -> str:
        """Convenience helper for a single, one-off question (no history)."""
        content = prompts.build_troubleshooting_prompt(user_message, faq_context)
        return self.reply([{"role": "user", "content": content}])
