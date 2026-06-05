"""Command-line chat interface.

This layer owns the conversation `history` and passes it to the (stateless)
LLM client on every turn. That's the practical consequence of the model having
no memory: WE remember the conversation and resend it each time.
"""

from helpdesk.auth.entra_auth import EntraAuth
from helpdesk.core.llm_client import LLMClient
from helpdesk.core.prompts import build_troubleshooting_prompt
from helpdesk.incidents.categorizer import categorize
from helpdesk.knowledge.knowledge_base import KnowledgeBase


def _greet() -> None:
    """Sign in with Microsoft Entra ID and greet the user by name.

    Optional by design: if Entra isn't configured, the app stays silent and
    runs unauthenticated. If sign-in is started but doesn't complete, we say so
    and carry on — the assistant still works without an identity.
    """
    auth = EntraAuth()
    if not auth.configured:
        return  # no Entra config -> run without sign-in

    profile = auth.sign_in()
    if profile:
        first_name = profile.name.split()[0] if profile.name else "there"
        print(f"\nWelcome, {first_name}! Signed in as {profile.email}.")
        if profile.department:
            print(f"  Department: {profile.department}")
    else:
        print("\n(Continuing without sign-in.)")


def run() -> None:
    print("=" * 60)
    print("  AI Help Desk Assistant  (type 'quit' to exit)")
    print("=" * 60)

    _greet()

    kb = KnowledgeBase()
    llm = LLMClient()
    history: list[dict] = []  # the running conversation we resend each turn

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break
        if not user_input:
            continue

        # 1. Categorize the request (rule-based, works offline).
        incident = categorize(user_input)
        print(f"\n  \u21b3 Categorized as: {incident.category.value} | priority: {incident.priority.value}")

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
