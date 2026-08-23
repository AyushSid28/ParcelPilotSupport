# ParcelPilot Support Copilot — Architecture

**Product:** Dual-context AI support system for ParcelPilot  
**Dataset snapshot (system “now”):** `2026-08-16 11:00 Asia/Kolkata`  
**Currency:** INR  
**Information base:** six PDFs + `ParcelPilot_Assessment_Data.xlsx` only

This document is the technical source of truth. Sequencing and GitHub slices: `PLAN.md`. Acceptance items: `CHECKLIST.md`.

---

## 1. Problem we are actually solving

ParcelPilot’s ops team answers questions by searching policies, customer contracts, product docs, old tickets, and operational tables. Those sources **conflict on purpose**:

- Policy v2 is deprecated and must never drive current answers.
- Signed agreements override default SOP and SLA.
- Closed tickets `TKT-450` and `TKT-451` contain **incorrect** past guidance.
- Known issues (KI-208, KI-211) are operational truth that can override naive status reads.

A chatbot that only “retrieves and answers” will fail. The system must **rank sources, refuse to invent process, confirm mutations, and isolate tenant data in the tool layer**.

Two extra client problems are first-class:

1. **Trust and reliability** — retrieval ranking, Python calculators, citations, escalation.
2. **Proactive issue detection** — internal Ops Pulse view, not only reactive chat.

---

## 2. Product surfaces

### 2.1 Customer Support Agent

Mocked logged-in customer. Can ask about *their* orders, tickets, contract, and current ParcelPilot policy.

Cannot see other accounts’ orders, tickets, or agreements.

Typical jobs: cancellation fee, failed-pickup credit, “why still BOOKED?”, plan capabilities, escalate.

### 2.2 Internal Ops Agent

Mocked ParcelPilot staff. Cross-account (by role). Classify severity, check SLA against snapshot time, apply contracts, prepare actions.

### 2.3 Ops Pulse (proactive)

Internal dashboard/API. Deterministic detectors over tickets + orders + known issues. The LLM may explain a cluster; it does not invent the cluster.

---

## 3. High-level system

```
┌─────────────────────────────────────────────────────────────┐
│  Web UI (Next.js)                                           │
│  Persona switcher · Chat · Tool timeline · Citations        │
│  Confirm-action card · Ops Pulse                            │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS JSON / SSE
┌───────────────────────────▼─────────────────────────────────┐
│  API (FastAPI)                                              │
│  Auth context middleware · SSE stream · Action lock         │
└─────────────┬───────────────────────────┬───────────────────┘
              │                           │
              ▼                           ▼
┌─────────────────────────┐   ┌───────────────────────────────┐
│  Agent runtime          │   │  Ops Pulse engine             │
│  LangGraph + tools      │   │  Rule detectors (no LLM req)  │
└─────────────┬───────────┘   └───────────────────────────────┘
              │
     ┌────────┼────────┬─────────────────┐
     ▼        ▼        ▼                 ▼
┌─────────┐ ┌──────┐ ┌──────────┐ ┌─────────────┐
│ Doc RAG │ │ SQL  │ │ Policy   │ │ Action store│
│ + ranks │ │ data │ │ calculators│ │ (mocked)  │
└─────────┘ └──────┘ └──────────┘ └─────────────┘
```

**Rule:** the model never reads Excel/PDF files directly. It only calls tools. Tools enforce ACL, snapshot time, and source metadata.

---

## 4. Stack (locked)

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | RAG, pandas, agent tooling |
| API | FastAPI + Uvicorn | Typed tools, SSE, easy host |
| Agent | LangGraph + OpenAI tool calling | Explicit multi-step graph |
| Embeddings | `text-embedding-3-small` | Enough for 6 short PDFs |
| Vectors | Chroma (persistent on disk) | Zero-ops at this size |
| Structured data | SQLite loaded from xlsx at boot | ACL queries, SLA math |
| PDF ingest | pypdf + heading-aware chunker | Tiny corpus; quality over parsers |
| Frontend | Next.js (App Router) + Tailwind | Chat + dashboard |
| Hosting | API on Render/Railway; UI on Vercel | Hosted link is highly preferred |
| Config | `.env` for `OPENAI_API_KEY` only | No secrets in git |

Agent code sits behind a provider interface so the chat model can change without rewriting tools.

---

## 5. Domain snapshot (evaluation gold)

All time math uses **2026-08-16 11:00 +05:30**.

### 5.1 Source precedence (hard)

1. Signed customer agreement for **that** `account_id` (if present)
2. Current SOP / support policy v3 / product guide
3. Open known issues (KI-208, KI-211)
4. Historical tickets — context only, never policy
5. Support Policy v2 — **excluded from default retrieval**; if seen, marked deprecated and unusable for answers

### 5.2 Accounts

| ID | Name | Plan | Contract | Effect |
|---|---|---|---|---|
| ACCT-001 | Northstar | Enterprise | Yes | P1 15m 24x7; cancel BOOKED pre-pickup **no fee**; credit SOP + ₹5,000 monthly cap |
| ACCT-002 | LumenWorks | Growth | Yes | No weekend/after-hours; no cancel waiver; failed-pickup **>4h → ₹300 fixed** |
| ACCT-003 | Beacon | Standard | No | Default SOP + v3 Standard SLA |
| ACCT-004 | Axis Labs | Enterprise | No | Default Enterprise v3 SLA; no cancel waiver |

### 5.3 Order gold answers

| Order | Correct behaviour |
|---|---|
| ORD-1001 | Northstar, BOOKED, cancel 2h after book → **cancel, ₹0**. Ignore TKT-450. |
| ORD-1002 | PICKED_UP → **do not cancel**; return-to-origin |
| ORD-2001 | LumenWorks, 75 min after book → **cancel, ₹250** |
| ORD-2002 | 4.5h late; carrier fault → **₹300** (not min(500, 10% of 2400)=₹240) |
| ORD-3001 | Beacon, 15 min after book → **cancel, ₹0** |
| ORD-4001 | DELIVERED → **cannot cancel** |

### 5.4 Ticket gold behaviour

| Ticket | Behaviour |
|---|---|
| TKT-501 | P1. Northstar 15m. Created 10:30 → **SLA breached**. Escalate. |
| TKT-502 | KI-208. Limit still **5,000** rows. Split below ~3,000. Do not repeat TKT-451. |
| TKT-503 | Billing-contact change **not in pack** → escalate |
| TKT-504 | KI-211 SwiftShip webhook ≤20 min. Do not claim pickup failed |
| TKT-505 | P1 credential exposure. Enterprise 30m. Created 08:30 → **breached**. Escalate |
| TKT-450 / 451 | Closed, **incorrect** resolutions |

---

## 6. Identity, tenancy, and ACL

Authentication is **mocked**. Enforcement is still real.

### 6.1 Request context

Every API request carries:

```text
X-Actor-Type: customer | staff
X-Account-Id: ACCT-00x          # required for customer
X-Staff-Id: priya|arjun|neha|rohit|maya
X-Staff-Role: csm | agent | ops_lead
```

The UI persona switcher sets these headers. The backend **never** trusts the model to remember who the user is.

### 6.2 Roles

| Role | Scope |
|---|---|
| `customer` | Only `account_id` in the header |
| `agent` | All accounts, read + propose actions |
| `csm` | All accounts; UI highlights their book |
| `ops_lead` | All accounts + Ops Pulse + high-credit approve |

### 6.3 Enforcement point

ACL lives in **repository functions**, not in the system prompt.

```text
get_order(order_id, ctx) ->
  row = db.orders.get(order_id)
  if not row: NotFound
  if ctx.actor == customer and row.account_id != ctx.account_id:
      NotFound          # same as missing — no existence leak
  return row
```

Document search:

- Customer: current policy/SOP/product + **only that account’s agreement**. Never other agreements. Never v2 by default.
- Staff: all current docs + all agreements. v2 only if explicitly searching deprecated/historical policy.

---

## 7. Document pipeline

### 7.1 Ingest

On boot or `scripts/ingest_docs.py`:

1. Extract text per PDF (preserve headings).
2. Split into chunks ~400–700 tokens, overlap ~80; keep bullets with their heading when possible.
3. Attach metadata:

```json
{
  "doc_id": "01_support_policy_v3",
  "filename": "01_Support_Policy_v3_CURRENT.pdf",
  "title": "Support Policy v3",
  "doc_type": "support_policy",
  "status": "current",
  "authority": 80,
  "effective_from": "2026-05-01",
  "account_id": null,
  "supersedes": "support_policy_v2"
}
```

Agreements: `account_id` = `ACCT-001` / `ACCT-002`, `authority` = 100.  
Deprecated v2: `status=deprecated`, `authority=0`.

### 7.2 Retrieval tool

`search_documents(query, ctx, doc_types=None)`:

1. Embed query.
2. Filter by ACL + `status != deprecated` (unless staff `include_deprecated=true`).
3. Take top k (8).
4. **Rerank in code** by `(authority, embedding_score)` — agreement chunks outrank policy when both match.
5. Return snippets with `filename`, `authority`, `status`, `account_id`, `effective_from`.

The agent must cite these filenames in the user-visible answer.

---

## 8. Structured data layer

Boot: read xlsx → SQLite (`data/parcelpilot.db`).

Tables: `accounts`, `orders`, `tickets`, plus write tables `escalations`, `ticket_updates`, `tasks`, `audit_log`.

Timestamps timezone-aware; comparisons use snapshot clock unless a test overrides.

### 8.1 Lookup tools (read)

| Tool | Purpose |
|---|---|
| `get_account` | Plan, CSM, contract flag, premium_support |
| `get_order` | Full order row |
| `list_orders` | Filtered by account (ACL) |
| `get_ticket` | Including `historical_resolution` labelled untrusted |
| `list_tickets` | Open/closed filters |
| `get_snapshot_time` | Canonical “now” |

### 8.2 Calculator tools (pure, testable)

SOP + contract encoded **in Python**, not in the LLM.

**`assess_cancellation(order_id, ctx)`** returns a structured verdict, for example:

```json
{
  "allowed": true,
  "fee_inr": 0,
  "reason_codes": ["STATUS_BOOKED", "CONTRACT_WAIVES_FEE"],
  "policy_basis": [
    "05_Northstar_Logistics_Enterprise_Agreement.pdf",
    "03_Cancellation_and_Service_Credit_SOP_v4.pdf"
  ],
  "conflicts": [
    { "ignored": "TKT-450", "why": "historical_ticket_not_authority" }
  ],
  "warnings": [],
  "requires_confirmation": true
}
```

Logic:

- DELIVERED → not allowed
- PICKED_UP → not allowed; suggest RTO
- DRAFT → allowed, fee 0
- BOOKED + Northstar contract → fee 0
- BOOKED + minutes since booked ≤ 30 → fee 0
- BOOKED + else → fee 250
- SwiftShip + BOOKED + pickup window started → attach KI-211 warning

**`assess_failed_pickup_credit(order_id, ctx)`**

- `carrier_fault` unknown → `uncertain`, do not promise
- `customer_fault` → ineligible
- Hours late = snapshot − `pickup_window_end` (if still not picked up) or actual − window end
- LumenWorks: eligible iff hours > 4; amount = 300
- Else: eligible iff hours > 2; amount = min(500, 0.10 * shipment_fee)
- Amount > 1000 → `requires_manager_approval`
- Northstar: monthly cap remaining (from action store; start at 5000)

**`classify_severity_and_sla(ticket_id, ctx)`**

- Complete shipment-create outage, security/credential → P1
- Major feature down with workaround → P2
- How-to / limited impact → P3

Returns target minutes, elapsed, `breached: bool`.

Unit-tested against the gold table in §5 so we never hard-code `ORD-1001`.

---

## 9. Agent runtime

### 9.1 Graph

```
START
  → load_context (actor, account, snapshot)
  → agent (LLM + tools)
       ↺ tools until stop OR action_proposal
  → if action_proposal: wait_for_user_confirmation
       → execute_action | cancel_action
  → respond (answer + citations + uncertainty)
END
```

Max tool rounds: 8. Then partial answer + offer escalation.

### 9.2 System policy (not a substitute for ACL)

- Snapshot time and timezone
- Precedence ladder
- Historical tickets untrusted
- Never use v2 for current advice
- Missing procedure (billing contact) → escalate
- Never promise a credit when fault/timing unknown
- Never mutate without confirm from the confirmation node
- Cite filenames and record IDs

### 9.3 Tools the model chooses among

1. **Document search** — `search_documents`
2. **Structured lookup / calculation** — `get_order`, `assess_*`
3. **State-changing** — `propose_escalation` / `propose_ticket_update` / `propose_task`

Three mutation proposers; all share one confirmation gate.

### 9.4 Confirmation protocol

1. Agent calls `propose_escalation(...)` with payload.
2. Tool **does not write**. Returns `proposal_id` + preview.
3. UI card: payload, sources, Confirm / Cancel.
4. Confirm hits `POST /actions/{proposal_id}/confirm` — only path that writes SQLite.
5. Second Confirm is idempotent. Proposals expire in 10 minutes. ACL re-checked at confirm time.

---

## 10. Trust and reliability (Problem 2)

| Mechanism | Where |
|---|---|
| Authority metadata + rerank | Retrieval |
| Calculators in Python | Cancellation / credits / SLA |
| Conflict objects on calculator output | e.g. TKT-450 vs contract |
| Deprecated corpus filtered | Ingest + search |
| Uncertainty states | `unknown_fault`, `missing_procedure`, `status_may_lag` |
| Citation chips | Every assistant message |
| Confidence: `grounded` / `partial` / `must_escalate` | Agent final payload |
| Historical resolution banner | Ticket tool returns `trust: low` |

Example conflict copy:

> A past ticket (TKT-450) told Northstar a ₹250 fee applied. That is historical and incorrect. The active enterprise agreement waives cancellation fees for BOOKED shipments before pickup.

---

## 11. Ops Pulse (Problem 1)

Detectors at snapshot time:

| Detector | Signal in this pack |
|---|---|
| `sla_breach_p1` | TKT-501 (15m), TKT-505 (30m) |
| `open_p1_security` | TKT-505 API key |
| `known_issue_cluster` | TKT-502 + TKT-451 + KI-208 |
| `status_lag_pattern` | TKT-504 + KI-211 + SwiftShip BOOKED |
| `multi_customer_product` | Bulk upload: LumenWorks now + historical |
| `failed_pickup_carrier` | ORD-2002 |

`GET /ops/pulse` → issue cards `{id, severity, title, evidence_ids, suggested_action}`.

Staff can ask “what needs attention?” and the agent calls `get_ops_pulse`.

---

## 12. API sketch

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Snapshot time, ingest status |
| GET | `/me` | Resolved actor from headers |
| POST | `/chat` | SSE: tokens, `tool_start`, `tool_end`, `proposal`, `final` |
| GET | `/ops/pulse` | Staff only |
| GET | `/tickets`, `/orders` | ACL lists for UI |
| POST | `/actions/{id}/confirm` | Mutation |
| POST | `/actions/{id}/cancel` | Drop proposal |

---

## 13. Frontend

**Chat:** message list, tool timeline, citation chips, confirmation modal, account chip.

**Ops Pulse:** detector cards; click opens chat with a seeded question.

Demo personas:

- Customer: Northstar / LumenWorks / Beacon / Axis
- Staff: Agent Maya, Agent Rohit, CSM Priya, Ops lead

---

## 14. What we will not build (intentional)

- Real SSO / IdP
- Real carrier webhooks
- Write-back to production ticketing SaaS
- Fine-tuned models
- Full RTO workflow beyond a mocked task

---

## 15. Reliability, eval, observability

- Unit tests for calculators (gold table)
- ACL tests: customer ACCT-001 cannot `get_order(ORD-2001)`
- Retrieval tests: current Enterprise P1 must not cite v2 1-hour as current
- Structured logs: `request_id`, actor, tool name, latency, proposal id

---

## 16. Hosting and run

```bash
cp .env.example .env
make dev          # api :8000 + web :3000
```

Hosted: public UI + API, CORS locked to the UI origin. README documents env vars and the frozen snapshot clock.

---

## 17. Demo narrative (~5 minutes)

1. Architecture (this document, ~45s)
2. Customer Northstar: cancel ORD-1001 — contract vs TKT-450, confirm
3. Customer LumenWorks: ORD-2002 credit ₹300 not ₹240
4. Ops: TKT-505 breach + Pulse card
5. Trust: v2 excluded; confirmation gate
6. Decision: calculators in code, ACL in repos, Pulse without LLM

---

## 18. Metric we would use in production

**Correct-and-grounded resolution rate:** % of conversations where the user did not reopen within 48h, the answer cited a current authoritative source, and human QA agrees the calculator verdict was applied.

Secondary: **unsafe-action rate** (mutation without confirmation or cross-tenant leak) must stay at 0.
