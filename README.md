# AI Help Desk Assistant

An enterprise IT support assistant that answers common help desk questions,
troubleshoots issues conversationally, categorizes incidents, and retrieves
answers from a knowledge base using semantic (vector) search. Built around the
Microsoft enterprise stack — the same systems an IT operations role actually
runs: Microsoft 365, Intune, Entra ID, VPN, and endpoint support.

> Built by an IT professional with enterprise help desk experience, as a
> hands-on demonstration of cloud + AI operations skills.

---

## Skills demonstrated

**Cloud & AI (Azure)**
- **Azure OpenAI** — chat completions (`gpt-4.1-mini`) for multi-turn troubleshooting, and embeddings (`text-embedding-3-small`) for semantic retrieval
- **Azure AI Search** — a vector index (HNSW, cosine similarity) used as the retrieval layer of a **RAG** pipeline
- **Resource provisioning & cost management** — resources deployed on free/credit tiers with budget alerts and spending guardrails
- **Secrets management** — all credentials kept in a git-ignored `.env`, never committed

**Software engineering**
- **Python** with a clean, modular architecture (separate layers for AI, knowledge base, incidents, and integrations)
- **Graceful degradation** — every external dependency (AI, embeddings, search) falls back safely when unavailable, so the app never hard-crashes
- **Automated tests** with `pytest`, written to run offline (no keys/network) so they stay reliable in CI
- **Git/GitHub** — incremental, well-described commit history

**IT domain knowledge**
- Incident categorization and priority assignment modeled on real service-desk workflows
- Knowledge base scenarios drawn from real M365 / Intune / identity / VPN / endpoint support

---

## What it does

| Capability | How it works |
|---|---|
| **Conversational troubleshooting** | Multi-turn chat via Azure OpenAI; conversation history is maintained so follow-up questions keep context |
| **Semantic knowledge base (RAG)** | A user question is embedded and matched against an Azure AI Search vector index — so "I can't get into my account" finds the password-reset FAQ even with no shared keywords |
| **Incident categorization** | Each request is sorted into a category and priority (rules-based, instant, no API needed) |
| **Offline fallback** | Without cloud credentials, the app still categorizes requests and runs keyword-based FAQ search |

---

## Architecture

```
config/                 # central settings; reads secrets from .env
helpdesk/
  core/                 # LLM client (Azure OpenAI chat)
  knowledge/            # knowledge base, embedder, Azure AI Search vector store
    data/faq.json       # the FAQ source data
  incidents/            # incident categorization + priority
  integrations/         # ServiceNow client (planned)
  interface/            # command-line interface
tests/                  # offline-safe pytest suite
index_faqs.py           # one-time script: embeds FAQs and loads the search index
main.py                 # entry point
```

The retrieval layer is decoupled: the knowledge base exposes a single
`search(query)` method, so the matching strategy (keyword → vector) was upgraded
without changing any calling code.

---

## Setup

Requires Python 3.10+, an Azure OpenAI resource (chat + embedding deployments),
and an Azure AI Search service.

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure credentials
copy .env.example .env          # then fill in your Azure values
# (cp on macOS/Linux)

# 4. Load the FAQ data into the search index (one time)
python index_faqs.py

# 5. Run
python main.py                  # try: "I can't get into my account"
pytest                          # run the test suite
```

All required `.env` values are documented in `.env.example`.

---

## Roadmap

**Done**
- [x] Conversational chat interface
- [x] Knowledge base lookup
- [x] Incident categorization + priority assignment
- [x] Live AI troubleshooting on Azure OpenAI (multi-turn)
- [x] Vector database / semantic search (RAG) on Azure AI Search

**Planned**
- [ ] Entra ID authentication (Microsoft identity sign-in via MSAL)
- [ ] LLM-assisted incident categorization
- [ ] ServiceNow integration (ticket creation via a developer instance)
- [ ] Web API (FastAPI) and a simple web UI

---

## Future ideas

- **Personal finance tracker variant** — the same architecture (LLM +
  categorizer + data store) could power a "sort my spending / track my bills"
  app by swapping IT incidents for transactions. A natural second portfolio
  project that would reuse most of what's here.

---

## Notes

- This is a portfolio/learning project. It uses a ServiceNow **developer
  instance** (not any production system) and simulated M365/Intune scenarios —
  no real company tenant or data is connected.
- Secrets live only in a local, git-ignored `.env`.
