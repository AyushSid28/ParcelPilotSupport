# ParcelPilot — Build Plan & GitHub Strategy

This is the execution plan. Architecture details: `ARCHITECTURE.md`. Tick boxes: `CHECKLIST.md`.

---

## 1. Product decisions (locked)

| Decision | Choice | Why |
|---|---|---|
| Surfaces | **Customer chat + Internal chat + Ops Pulse** | Assessment allows one bot; both contexts plus proactive detection shows product judgment |
| Extra problems | **Both**: trust as core design, Pulse as a real view | Trust is required to answer the pack correctly; Pulse is the visible “beyond chatbot” piece |
| Mutations | Mocked SQLite escalations / ticket updates / tasks | Confirmation gate is the point, not Jira |
| Auth | Header persona switcher | ACL still real in repositories |
| Agent | LangGraph + OpenAI tools | Inspectable multi-step, not a single mega-prompt |
| Calculators | Python, unit-tested | Prevents “LLM did the ₹250 vs ₹0 math” |
| Hosting | FastAPI + Next.js, public URL | “Hosted link highly preferred” |
| Data | PDFs + xlsx only; snapshot clock frozen | Do not hard-code ORD-1001 answers in the agent |

---

## 2. Names

### Product name (shown in the UI)

| Name | Why |
|---|---|
| **ParcelPilot Support Copilot** | Clear, professional, default |
| **ParcelPilot Grounded Support** | Leans into trust / source ranking |
| **Pulse** (internal) + **ParcelPilot Help** (customer) | Two-surface branding if we split nav |
| **PilotAssist** | Short; weaker on a hiring README |

Default UI title: **ParcelPilot Support Copilot**. Ops page subtitle: **Ops Pulse**.

### GitHub repository name

Chosen repo (created):

**[`AyushSid28/ParcelPilotSupport`](https://github.com/AyushSid28/ParcelPilotSupport)**

Product name in the UI remains **ParcelPilot Support Copilot**.

| Name | Tone |
|---|---|
| **`parcelpilot-support-copilot`** | Best default — product, not homework |
| `parcelpilot-grounded-agent` | Trust + agent; strong for this assessment |
| `parcelpilot-ops-pulse` | Memorable; undersells the customer chatbot |
| `parcelpilot-ops-agent` | Internal-ops leaning |
| `parcelpilot-support-desk` | Familiar “desk” metaphor |
| `pp-policy-agent` | Policy/conflict focus; a bit cryptic |
| `northstar-support-agent` | Catchy (uses a customer name); too narrow |
| `calquity-parcelpilot-agent` | Ties to the employer; looks more like a take-home |

GitHub description (one line):

> Grounded support copilot for ParcelPilot — tenant-scoped tools, contract-aware policy, and an internal ops pulse.

Visibility: **public** (submission requires a public repo).

Do **not** commit `.env`, API keys, or `node_modules` / `__pycache__` / Chroma raw dumps if they contain nothing secret but are bulky — commit ingest *code* and source PDFs/xlsx.

---

## 3. Monorepo layout (create incrementally, not in one dump)

```text
parcelpilot-support-copilot/
  README.md
  LICENSE                    # optional MIT
  .gitignore
  .env.example
  Makefile
  docs/
    ARCHITECTURE.md
    PLAN.md
    CHECKLIST.md
    ARCHITECTURE_NOTE.md     # short submission note (later)
    PRODUCT_NOTE.md          # short submission note (later)
  data/
    source/                  # the six PDFs + xlsx (gitkept)
    parcelpilot.db           # generated, gitignored
  backend/
    pyproject.toml
    app/
      main.py
      config.py
      auth/
      db/
      retrieval/
      tools/
      agent/
      ops/
      api/
    tests/
    scripts/ingest_docs.py
  web/
    package.json
    app/ ...
  demo/
    SCRIPT.md                # video outline (late)
```

---

## 4. GitHub narrative — why incremental commits

Reviewers often open **git log**. One giant commit looks like a paste. We will push **thin vertical slices** that each run or test something.

Rules for every commit:

- Message: imperative, why not file list (`Add tenant ACL on order lookup`).
- Each commit leaves the repo runnable *for what exists* (tests or a stub server).
- No “WIP asdf” on `main`.
- Docs-first commits are fine; they prove we designed before coding.

Suggested `main` history (squash locally only if a slice went messy **before** it was pushed; after push, new commits to fix).

---

## 5. Commit slices (build order)

Do these in order. Each slice = implement → test/smoke → commit → `git push`.

### Slice 0 — Repo skeleton  
**Commit:** `Initialize ParcelPilot support copilot repo`  
README (what it will be), `.gitignore`, `.env.example`, copy `docs/` and `data/source/`.  
No agent yet.

### Slice 1 — Domain data boot  
**Commit:** `Load assessment workbook into SQLite`  
Parse xlsx → schema → seed. `GET /health` returns snapshot time and row counts.  
Tests: 4 accounts, 6 orders, 7 tickets.

### Slice 2 — Policy calculators  
**Commit:** `Encode cancellation, credit, and SLA rules in code`  
Pure functions + gold-table tests (ORD-1001 fee 0, ORD-2001 fee 250, ORD-2002 credit 300, TKT-505 breached, …).  
This is the highest-signal engineering commit.

### Slice 3 — Tenant ACL  
**Commit:** `Enforce account isolation in the data layer`  
Customer context cannot read foreign orders/tickets/agreements. Tests for NotFound vs leak.

### Slice 4 — Document ingest + ranked retrieval  
**Commit:** `Ingest policies with authority metadata`  
v2 marked deprecated; agreements tagged to account. Test: current Enterprise P1 ≠ v2 1 hour as top current hit.

### Slice 5 — Read tools  
**Commit:** `Expose lookup and document search as agent tools`  
JSON schemas, ACL wrapped. No LLM required to unit-test tools.

### Slice 6 — Mutation proposals + confirm  
**Commit:** `Require explicit confirmation before state changes`  
Propose → persist preview → confirm writes `escalations` / `tasks`. Double-confirm idempotent.

### Slice 7 — LangGraph agent  
**Commit:** `Add multi-step agent loop over tools`  
SSE events: `tool_start` / `tool_end` / `final`. System prompt with precedence.  
Manual smoke: ORD-1001 question.

### Slice 8 — Chat UI  
**Commit:** `Add persona chat UI with tool timeline`  
Persona switcher, citations, confirm card.

### Slice 9 — Ops Pulse  
**Commit:** `Detect SLA breaches and issue clusters for ops`  
Detectors + `/ops/pulse` + Pulse page. TKT-501, TKT-505, KI-208 cluster visible without chatting.

### Slice 10 — Agent + Pulse wiring polish  
**Commit:** `Ground answers with citations and conflict warnings`  
Conflict banners (TKT-450), KI-211 warning on SwiftShip BOOKED, escalate-when-missing-SOP (TKT-503).

### Slice 11 — Hosting  
**Commit:** `Add production run config for hosted demo`  
Docker or Render/Vercel files, CORS, README runbook.

### Slice 12 — Submission notes  
**Commit:** `Add architecture and product notes for submission`  
Short notes + AI-tool usage blurb + demo script.

Do **not** merge slices 7–10 into one push if they land on the same day — still separate commits even if pushed together.

---

## 6. Engineering sequence inside a slice

1. Write or extend a failing test (calculators, ACL, retrieval).
2. Implement the smallest code that passes.
3. Hit the API or UI path once.
4. Commit and push.

No feature flags needed; unused UI routes can land later.

---

## 7. Environment

- Python 3.12, Node 20+
- `OPENAI_API_KEY` for embeddings + chat
- Optional `OPENAI_MODEL=gpt-4.1` (or current equivalent at build time)
- `PARCELPILOT_SNAPSHOT=2026-08-16T11:00:00+05:30` (default)

---

## 8. Demo questions (must work without hard-coded IDs)

Customer / Northstar:

- Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.
- Can we cancel ORD-1002?

Customer / LumenWorks:

- Pickup is late and the carrier accepted fault on ORD-2002. Should I get a service credit? How much?
- Can I cancel ORD-2001 without a fee?

Customer / Beacon:

- Cancel ORD-3001 — any fee?

Staff:

- What needs attention right now?
- TKT-505 — have we breached SLA?
- Bulk upload failing for a 4,200-row file — plan limit or known issue?
- Change billing contact on Beacon?

Staff trap:

- What does policy v2 say we should do for Enterprise P1? → must say superseded, use v3 / contract.

---

## 9. After code freeze

1. Host UI + API.
2. Record ~5 min video from `demo/SCRIPT.md`.
3. Fill Google Form: repo, URL, video, notes, AI-tool usage.
4. Stop adding features; only fix demo-breakers.

---

## 10. Next action

Create the GitHub repo as **`parcelpilot-support-copilot`**, then execute **Slice 0** (skeleton + these docs + source pack) as the first push.
