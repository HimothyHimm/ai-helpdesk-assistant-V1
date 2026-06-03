"""Prompt templates for the AI model.

Keeping prompts in their own file (instead of scattered through the code) means
you can read, tweak, and version them in one place — which matters a lot, because
prompt wording is where most of the assistant's "personality" and accuracy live.
"""

SYSTEM_PROMPT = """You are an IT help desk assistant for an enterprise company.
You help employees troubleshoot common IT issues clearly and patiently.

Guidelines:
- Ask one clarifying question at a time if the problem is vague.
- Give step-by-step instructions a non-technical employee can follow.
- If the issue may be a security incident (phishing, malware, breach), tell the
  user to stop and contact the security team immediately.
- If you don't know, say so and recommend opening a ticket — never guess.
- Keep answers concise.
"""


def build_troubleshooting_prompt(user_message: str, faq_context: str | None = None) -> str:
    """Combine the user's message with any relevant FAQ context we found."""
    if faq_context:
        return (
            f"Here is a relevant entry from our internal IT knowledge base:\n"
            f"{faq_context}\n\n"
            f"Using that as your primary source, answer the user's question:\n"
            f"{user_message}"
        )
    return user_message
