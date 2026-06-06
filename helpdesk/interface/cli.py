"""Command-line chat interface.

This layer owns the conversation `history` and passes it to the (stateless)
LLM client on every turn. That's the practical consequence of the model having
no memory: WE remember the conversation and resend it each time.

Commands:
  quit / exit / q  - leave the assistant
  ticket           - create a ServiceNow incident from the current issue
"""

from helpdesk.auth.entra_auth import EntraAuth
from helpdesk.core.llm_client import LLMClient
from helpdesk.core.prompts import build_troubleshooting_prompt
from helpdesk.incidents.categorizer import categorize
from helpdesk.integrations.servicenow_client import ServiceNowClient
from helpdesk.knowledge.knowledge_base import KnowledgeBase


def _greet():
    """Sign in with Microsoft Entra ID and greet the user. Returns the profile or None."""
    auth = EntraAuth()
    if not auth.configured:
        return None
    profile = auth.sign_in()
    if profile:
        first_name = profile.name.split()[0] if profile.name else "there"
        print(f"\nWelcome, {first_name}! Signed in as {profile.email}.")
        if profile.department:
            print(f"  Department: {profile.department}")
    else:
        print("\n(Continuing without sign-in.)")
    return profile


def _create_ticket(last_issue, last_incident, profile):
    """Create a ServiceNow incident from the most recent issue."""
    if last_issue is None:
        print("\n  Nothing to log yet - describe an issue first, then type 'ticket'.")
        return

    client = ServiceNowClient()
    if not client.configured:
        print("\n  ServiceNow isn't configured, so I can't create a ticket.")
        return

    # The Entra account may not exist as a ServiceNow user, so we record the
    # reporter in the description rather than the caller_id field.
    reporter = f"{profile.name} <{profile.email}>" if profile else "unknown (not signed in)"
    description = f"Reported by: {reporter}\n\nIssue: {last_issue}"

    print("\n  Creating a ServiceNow incident...")
    incident = client.create_incident(
        short_description=last_issue,
        description=description,
        category=last_incident.category.value,
        priority=last_incident.priority.value,
    )
    if incident:
        print(f"  Created incident {incident.number}")
        print(f"  View it: {incident.url}")
    else:
        print("  The request was sent but no reply came back - the ticket may still")
        print("  have been created. Check the incident list in your instance.")


def run() -> None:
    print("=" * 60)
    print("  AI Help Desk Assistant")
    print("  Commands: 'ticket' to log a ServiceNow incident, 'quit' to exit")
    print("=" * 60)

    profile = _greet()

    kb = KnowledgeBase()
    llm = LLMClient()
    history: list[dict] = []   # the running conversation we resend each turn
    last_issue = None          # the most recent user-described problem
    last_incident = None       # its categorization (category + priority)

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break
        if not user_input:
            continue
        if user_input.lower() == "ticket":
            _create_ticket(last_issue, last_incident, profile)
            continue

        # 1. Categorize the request (rule-based, works offline).
        incident = categorize(user_input)
        print(f"\n  \u21b3 Categorized as: {incident.category.value} | priority: {incident.priority.value}")
        last_issue = user_input
        last_incident = incident

        # 2. Look for a known answer in the knowledge base.
        match = kb.search(user_input)
        faq_context = None
        if match:
            faq_context = match.answer
            print(f"\n  \U0001F4D6 Knowledge base match: {match.question}")

        # 3. Build this turn's message (optionally grounded in the FAQ answer),
        #    add it to the running history, and send the WHOLE history to the AI.
        content = build_troubleshooting_prompt(user_input, faq_context)
        history.append({"role": "user", "content": content})

        ai_reply = llm.reply(history)
        print(f"\nAssistant: {ai_reply}")

        # 4. Record the assistant's turn so the next message has full context.
        history.append({"role": "assistant", "content": ai_reply})


if __name__ == "__main__":
    run()