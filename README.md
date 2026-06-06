# AI Help Desk Assistant

An enterprise IT support assistant that signs users in with their Microsoft
account, answers common help desk questions, troubleshoots issues
conversationally, categorizes incidents, retrieves answers from a knowledge base
using semantic (vector) search, and logs tickets to ServiceNow. Built around the
Microsoft enterprise stack and the ITSM tooling an IT operations role actually
runs: Microsoft 365, Entra ID, Intune, VPN, endpoints, and ServiceNow.

> Built by an IT professional with enterprise help desk experience, as a
> hands-on demonstration of cloud + AI operations skills.

---

## Skills demonstrated

**Cloud & AI (Azure + Microsoft 365)**
- **Azure OpenAI** — chat completions (`gpt-4.1-mini`) for multi-turn troubleshooting, and embeddings (`text-embedding-3-small`) for semantic retrieval
- **Azure AI Search** — a vector index (HNSW, cosine similarity) used as the retrieval layer of a **RAG** pipeline
- **Microsoft Entra ID + Microsoft Graph** — user sign-in via the OAuth 2.0 **device code flow** (MSAL), with a token cache for silent re-authentication, then a Graph call to read the signed-in user's profile
- **Resource provisioning & cost management** — resources deployed on free/credit tiers with budget alerts and spending guardrails
- **Secrets management** — credentials and tokens kept in git-ignored files (`.env`, token cache), never committed

**Integrations & software engineering**
- **ServiceNow** — incident creation through the REST **Table API** (basic auth against a developer instance), mapping the app's category and priority to ServiceNow fields
- **Python** with a clean, modular architecture (separate layers for auth, AI, knowledge base, incidents, and integrations)
- **Graceful degradation** — every external dependency (AI, embeddings, search, sign-in, ServiceNow) falls back safely when unavailable, so the app never hard-crashes
- **Automated tests** with `pytest`, written to run offline (no keys/network) so they stay reliable in CI
- **Git/GitHub** — incremental, well-described commit history

**IT domain knowledge**
- Microsoft identity (Entra ID) sign-in and Graph profile lookup
- Incident categorization and priority assignment modeled on real service-desk workflows
- ServiceNow incident logging from a support conversation
- Knowledge base scenarios drawn from real M365 / Intune / identity / VPN / endpoint support

---

## What it does

| Capability | How it works |
|---|---|
| **Microsoft sign-in** | Sign in with your Entra ID account via the device code flow; the app greets you by name and reads your profile from Microsoft Graph. Tokens are cached, so sign-in is silent after the first time |
| **Conversational troubleshooting** | Multi-turn chat via Azure OpenAI; conversation history is maintained so follow-up questions keep context |
| **Semantic knowledge base (RAG)** | A user question is embedded and matched against an Azure AI Search vector index, so "I can't get into my account" finds the password-reset FAQ even with no shared keywords |
| **Incident categorization** | Each request is sorted into a category and priority (rules-based, instant, no API needed) |
| **ServiceNow ticket logging** | Type `ticket` to turn the current issue into a ServiceNow incident; the auto-assigned category and priority map to ServiceNow fields, and the signed-in user is recorded as the reporter |
| **Offline fallback** | Without cloud credentials, the app still runs unauthenticated, categorizes requests, and does keyword-based FAQ search |

---

## Architecture

```
config/                 # central settings; reads secrets from .env
helpdesk/
  auth/                 # Microsoft Entra ID sign-in (MSAL) + Graph profile
  core/                 # LLM client (Azure OpenAI chat)
  knowledge/            # knowledge base, embedder, Azure AI Search vector store
    data/faq.json       # the FAQ source data
  incidents/            # incident categorization + priority
  integrations/         # ServiceNow client (incident creation via Table API)
  interface/            # command-line interface
tests/                  # offline-safe pytest suite
index_faqs.py           # one-time script: embeds FAQs and loads the search index
main.py                 # entry point
```

The layers are decoupled: the knowledge base exposes a single `search(query)`
method (keyword to vector), sign-in is an optional `EntraAuth().sign_in()` step
at startup, and ServiceNow is reached through a small `ServiceNowClient` — so
each piece can change without touching the others.

---

## Setup

Requires Python 3.10+, an Azure OpenAI resource (chat + embedding deployments),
an Azure AI Search service, a Microsoft Entra ID app registration (public client,
"Allow public client flows" enabled, `User.Read` Graph permission), and a free
ServiceNow Personal Developer Instance.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
copy .env.example .env          # then fill in your Azure, Entra, and ServiceNow values
# (cp on macOS/Linux)

# 4. Load the FAQ data into the search index (one time)
python index_faqs.py

# 5. Run
python main.py                  # sign in, ask a question, type 'ticket' to log it
pytest                          # run the test suite
```

All required `.env` values are documented in `.env.example`. The first launch
signs you in via the device code flow; after that, the cached token signs you in
silently.

---

## Roadmap

**Done**
- [x] Conversational chat interface
- [x] Knowledge base lookup
- [x] Incident categorization + priority assignment
- [x] Live AI troubleshooting on Azure OpenAI (multi-turn)
- [x] Vector database / semantic search (RAG) on Azure AI Search
- [x] Microsoft Entra ID sign-in (device code flow) + Graph profile + silent token cache
- [x] ServiceNow integration — incident creation via the REST Table API

**Planned**
- [ ] LLM-assisted incident categorization
- [ ] Web API (FastAPI) and a simple web UI

---

## Future ideas

- **Personal finance tracker variant** — the same architecture (LLM +
  categorizer + data store) could power a "sort my spending / track my bills"
  app by swapping IT incidents for transactions. A natural second portfolio
  project that would reuse most of what's here.

---

## Notes

- This is a portfolio/learning project. ServiceNow integration runs against a
  **Personal Developer Instance** (not any production system), and the
  M365/Intune scenarios are simulated — no real company tenant or data is
  connected beyond the developer's own test Entra tenant used for sign-in.
- Secrets and tokens live only in local, git-ignored files (`.env`,
  `.token_cache.json`). For production, the ServiceNow auth would move to OAuth
  and the token cache to an OS keychain.
