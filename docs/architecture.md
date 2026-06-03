# Architecture

This document explains *why* the project is structured the way it is. Read this
when you want to understand the design rather than the code.

## Guiding idea: separate the four jobs

The assistant does four very different kinds of work. Mixing them in one big file
would make the project impossible to grow. So each lives in its own module with a
narrow, well-defined job:

```
        ┌─────────────────────────────────────────────┐
        │              interface/ (CLI)                │  ← the user talks here
        │   thin glue layer; almost no logic of its own │
        └───────┬───────────┬───────────┬──────────────┘
                │           │           │
       ┌────────▼──┐  ┌─────▼──────┐  ┌─▼────────────┐
       │ incidents/│  │ knowledge/ │  │   core/      │
       │ categorize│  │  FAQ / RAG │  │ AI (LLM)     │
       └───────────┘  └────────────┘  └──────────────┘
                                              │
                                      ┌───────▼────────┐
                                      │ integrations/  │
                                      │  ServiceNow    │
                                      └────────────────┘

        config/  →  settings & secrets, used by everything
```

## Why this helps you specifically

- **You can ship value before touching AI.** The categorizer and knowledge base
  work with zero API keys. That means a working demo on day one.
- **Each piece is swappable.** Version 1 of the categorizer uses keyword rules.
  Version 2 will use the LLM. Because everything else only depends on the
  `categorize()` function's inputs and outputs, the upgrade is contained.
- **Secrets stay out of the code.** API keys and ServiceNow passwords live in
  `.env` (git-ignored) and are read only through `config/settings.py`.

## The "stub then implement" pattern

`llm_client.py` and `servicenow_client.py` are *stubs*: they have the final shape
(class names, method signatures) but return placeholders instead of doing real
work. This lets the app run end to end immediately, and means later steps only
fill in one method without rewiring the project.

## Where each capability gets built up

| Capability        | v1 (now)            | v2 (later)                          |
|-------------------|---------------------|-------------------------------------|
| Categorization    | keyword rules       | LLM, with rules as fallback         |
| Knowledge base    | keyword FAQ search  | semantic / vector search (RAG)      |
| Troubleshooting   | stubbed             | real Anthropic API call             |
| ServiceNow        | stubbed             | real REST API calls                 |
| Interface         | CLI                 | + FastAPI web API and web UI        |
