"""
FastAPI web interface for the AI Help Desk Assistant.

Wraps the SAME logic the CLI uses - categorizer, knowledge base, Azure OpenAI,
ServiceNow - behind a small HTTP API, and serves a lightweight chat page so the
assistant can be used in a browser instead of the terminal.

Run:
    python webapp.py
Then open http://127.0.0.1:8000   (auto-generated API docs at /docs).

Design notes
------------
- STATELESS chat, exactly like the CLI: the browser holds the conversation and
  sends the full history with each message; the server reuses
  LLMClient.reply(history). Nothing about the conversation is stored server-side.
- The web UI is intentionally sign-in free. Microsoft Entra ID sign-in is built
  and proven in the CLI (device-code flow, which suits a terminal); browser SSO
  is a separate, additive project. So the web app focuses on chat + ticketing.
- Same graceful degradation as the rest of the app: without cloud credentials it
  still returns categorization and keyword-based FAQ matches.
"""

from __future__ import annotations

from typing import List, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from helpdesk.core.llm_client import LLMClient
from helpdesk.core.prompts import build_troubleshooting_prompt
from helpdesk.incidents.categorizer import categorize
from helpdesk.integrations.servicenow_client import ServiceNowClient
from helpdesk.knowledge.knowledge_base import KnowledgeBase

app = FastAPI(title="AI Help Desk Assistant")

# Built once and reused across requests - all stateless.
_kb = KnowledgeBase()
_llm = LLMClient()


# --------------------------------------------------------------------------- #
# Request / response models                                                    #
# --------------------------------------------------------------------------- #
class Message(BaseModel):
    role: str        # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []   # prior turns, oldest first (browser-owned)


class ChatResponse(BaseModel):
    reply: str
    category: str
    priority: str
    kb_question: Optional[str] = None


class TicketRequest(BaseModel):
    issue: str
    category: str = ""
    priority: str = "medium"


class TicketResponse(BaseModel):
    created: bool
    number: Optional[str] = None
    url: Optional[str] = None
    detail: str = ""


# --------------------------------------------------------------------------- #
# API endpoints                                                                #
# --------------------------------------------------------------------------- #
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """Categorize the message, look for a known answer, and get an AI reply.

    The browser sends the running history; we rebuild the message list, append
    the new (FAQ-grounded) turn, and call the stateless LLM client. Only the
    current turn is grounded with FAQ context - past replies already reflect
    theirs, so we don't re-inject stale context.
    """
    incident = categorize(req.message)

    match = _kb.search(req.message)
    faq_context = match.answer if match else None
    kb_question = match.question if match else None

    history = [{"role": m.role, "content": m.content} for m in req.history]
    history.append({
        "role": "user",
        "content": build_troubleshooting_prompt(req.message, faq_context),
    })
    reply = _llm.reply(history)

    return ChatResponse(
        reply=reply,
        category=incident.category.value,
        priority=incident.priority.value,
        kb_question=kb_question,
    )


@app.post("/ticket", response_model=TicketResponse)
def ticket(req: TicketRequest) -> TicketResponse:
    """Create a ServiceNow incident from the supplied issue."""
    client = ServiceNowClient()
    if not client.configured:
        return TicketResponse(created=False, detail="ServiceNow isn't configured.")

    # Capture the client's status messages instead of printing to a console.
    notes: List[str] = []
    created = client.create_incident(
        short_description=req.issue,
        description=f"Reported via web UI.\n\nIssue: {req.issue}",
        category=req.category,
        priority=req.priority,
        prompt=notes.append,
    )
    if created:
        return TicketResponse(
            created=True,
            number=created.number,
            url=created.url,
            detail=f"Created incident {created.number}.",
        )
    # No object back: either a captured error, or the known return-path drop on
    # this machine (where the ticket is usually created anyway).
    detail = " ".join(notes) or (
        "The request was sent but no confirmation came back - the ticket may "
        "still have been created. Check the incident list in your instance."
    )
    return TicketResponse(created=False, detail=detail)


# --------------------------------------------------------------------------- #
# Web UI (single inline page, vanilla JS - no build step)                      #
# --------------------------------------------------------------------------- #
_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Help Desk Assistant</title>
<style>
  :root { --bg:#0f172a; --panel:#ffffff; --ink:#0f172a; --muted:#64748b;
          --line:#e2e8f0; --user:#2563eb; --bot:#f1f5f9; --accent:#2563eb; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
         background: linear-gradient(180deg,#0f172a,#1e293b); color: var(--ink);
         min-height:100vh; display:flex; justify-content:center; }
  .app { width:100%; max-width:720px; margin:24px 16px; background:var(--panel);
         border-radius:14px; box-shadow:0 12px 40px rgba(0,0,0,.35);
         display:flex; flex-direction:column; overflow:hidden; height:calc(100vh - 48px); }
  header { padding:18px 22px; border-bottom:1px solid var(--line); }
  header h1 { margin:0; font-size:18px; }
  header p { margin:4px 0 0; color:var(--muted); font-size:13px; }
  #log { flex:1; overflow-y:auto; padding:18px 22px; display:flex; flex-direction:column; gap:14px; }
  .msg { max-width:80%; padding:10px 14px; border-radius:12px; line-height:1.45; font-size:14px; white-space:pre-wrap; word-wrap:break-word; }
  .msg.user { align-self:flex-end; background:var(--user); color:#fff; border-bottom-right-radius:4px; }
  .msg.bot  { align-self:flex-start; background:var(--bot); color:var(--ink); border-bottom-left-radius:4px; }
  .meta { align-self:flex-start; font-size:12px; color:var(--muted); margin:-6px 0 0 2px; display:flex; gap:6px; flex-wrap:wrap; }
  .badge { background:#eef2ff; color:#3730a3; border-radius:999px; padding:2px 9px; font-weight:600; }
  .badge.pri-high, .badge.pri-critical { background:#fee2e2; color:#b91c1c; }
  .badge.kb { background:#ecfdf5; color:#047857; }
  .composer { border-top:1px solid var(--line); padding:14px 16px; display:flex; gap:10px; }
  #input { flex:1; resize:none; border:1px solid var(--line); border-radius:10px; padding:11px 12px; font:inherit; font-size:14px; }
  #input:focus { outline:2px solid var(--accent); outline-offset:0; border-color:var(--accent); }
  button { border:0; border-radius:10px; padding:0 16px; font:inherit; font-weight:600; cursor:pointer; }
  #send { background:var(--accent); color:#fff; }
  #send:disabled { opacity:.5; cursor:default; }
  .ticketbar { border-top:1px solid var(--line); padding:12px 16px; display:flex; align-items:center; gap:12px; background:#f8fafc; }
  #ticket { background:#0f766e; color:#fff; padding:9px 14px; }
  #ticket:disabled { opacity:.5; cursor:default; }
  #status { font-size:13px; color:var(--muted); }
  #status a { color:var(--accent); }
</style>
</head>
<body>
  <div class="app">
    <header>
      <h1>AI Help Desk Assistant</h1>
      <p>Describe an IT issue. I'll categorize it, check the knowledge base, and help troubleshoot.</p>
    </header>
    <div id="log"></div>
    <div class="composer">
      <textarea id="input" rows="1" placeholder="e.g. I can't connect to the VPN from home"></textarea>
      <button id="send">Send</button>
    </div>
    <div class="ticketbar">
      <button id="ticket" disabled>Create ServiceNow ticket</button>
      <span id="status">Send a message first, then you can log it as a ticket.</span>
    </div>
  </div>
<script>
  const log = document.getElementById("log");
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("send");
  const ticketBtn = document.getElementById("ticket");
  const status = document.getElementById("status");

  let history = [];          // [{role, content}] - the browser owns the conversation
  let last = null;           // {issue, category, priority} for ticketing

  function bubble(text, who) {
    const div = document.createElement("div");
    div.className = "msg " + who;
    div.textContent = text;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
    return div;
  }

  function meta(category, priority, kbQuestion) {
    const div = document.createElement("div");
    div.className = "meta";
    div.innerHTML =
      '<span class="badge">' + category + '</span>' +
      '<span class="badge pri-' + priority + '">priority: ' + priority + '</span>';
    if (kbQuestion) {
      const kb = document.createElement("span");
      kb.className = "badge kb";
      kb.textContent = "KB: " + kbQuestion;
      div.appendChild(kb);
    }
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  async function send() {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendBtn.disabled = true;
    bubble(text, "user");
    const thinking = bubble("...", "bot");

    try {
      const res = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: history })
      });
      const data = await res.json();
      thinking.textContent = data.reply;
      meta(data.category, data.priority, data.kb_question);

      history.push({ role: "user", content: text });
      history.push({ role: "assistant", content: data.reply });

      last = { issue: text, category: data.category, priority: data.priority };
      ticketBtn.disabled = false;
      status.textContent = "Ready to log this issue as a ServiceNow incident.";
    } catch (e) {
      thinking.textContent = "Something went wrong reaching the server. Is it still running?";
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  async function createTicket() {
    if (!last) return;
    ticketBtn.disabled = true;
    status.textContent = "Creating incident...";
    try {
      const res = await fetch("/ticket", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(last)
      });
      const data = await res.json();
      if (data.created && data.url) {
        status.innerHTML = "Created " + data.number +
          ' - <a href="' + data.url + '" target="_blank" rel="noopener">view incident</a>';
      } else {
        status.textContent = data.detail || "Could not confirm ticket creation.";
      }
    } catch (e) {
      status.textContent = "Something went wrong reaching the server.";
    } finally {
      ticketBtn.disabled = false;
    }
  }

  sendBtn.addEventListener("click", send);
  ticketBtn.addEventListener("click", createTicket);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  });
  input.focus();
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return _PAGE


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)