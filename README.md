# AI Help Desk Assistant

An AI-powered IT help desk assistant that answers common support questions,
guides users through troubleshooting, automatically categorizes incidents, and
(later) creates tickets in ServiceNow.

Built by an IT support professional learning to ship real software.

## What it does (and the order we're building it)

| Capability            | What it solves                              | Module          | Status |
|-----------------------|---------------------------------------------|-----------------|--------|
| Incident categorizing | Sort a request into a category + priority   | `incidents/`    | ✅ v1 (rules) |
| Knowledge base / FAQ  | Look up answers from your own IT docs       | `knowledge/`    | ✅ v1 (search) |
| AI troubleshooting    | Conversational, step-by-step help           | `core/`         | ✅ v1 (live) |
| ServiceNow            | Create/update real tickets                  | `integrations/` | 🔜 later |

The first three work today; the AI troubleshooting needs an API key (see below).
Only the ServiceNow piece is still stubbed, so the app runs end to end from day one.

## Turning on the AI (Step 2)

1. Get an API key from https://console.anthropic.com
2. Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY=...`
3. `pip install -r requirements.txt`
4. `python main.py` — answers are now live and remember the conversation.

Without a key, the assistant still categorizes requests and searches the FAQ; it
just returns a friendly "AI not configured" note instead of a live answer.

## Quick start

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd ai-helpdesk-assistant

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the example env file and fill it in later (not needed yet)
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux

# 5. Run the assistant
python main.py
```

## Project structure

```
ai-helpdesk-assistant/
├── main.py                      # Entry point — run this
├── requirements.txt             # Python dependencies
├── .env.example                 # Template for secrets (copy to .env)
├── .gitignore
├── config/
│   └── settings.py              # Loads config + secrets from .env
├── helpdesk/                    # The actual application package
│   ├── core/                    # The "brain": talks to the AI model
│   │   ├── llm_client.py
│   │   └── prompts.py
│   ├── knowledge/               # Answers from your own IT docs (FAQ)
│   │   ├── knowledge_base.py
│   │   └── data/faq.json
│   ├── incidents/               # Categorize + prioritize requests
│   │   ├── models.py
│   │   └── categorizer.py
│   ├── integrations/            # External systems (ServiceNow)
│   │   └── servicenow_client.py
│   └── interface/               # How users talk to the assistant
│       └── cli.py
├── tests/                       # Automated tests (pytest)
│   └── test_categorizer.py
└── docs/
    └── architecture.md          # Deeper explanation of the design
```

## Running the tests

```bash
pytest
```

## Roadmap

- [x] **Step 1** — Project architecture & folder structure
- [x] **Step 2** — Wire up the LLM client for real AI answers (you are here)
- [ ] **Step 3** — Grow the knowledge base into semantic search (RAG)
- [ ] **Step 4** — Upgrade the categorizer with the LLM
- [ ] **Step 5** — ServiceNow integration (create tickets)
- [ ] **Step 6** — Web API (FastAPI) and a simple web UI
