# ParcelPilot — Implementation Checklist

Use this while building. Architecture: `ARCHITECTURE.md`. Order of work: `PLAN.md`.

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

---

## A. Repo and hygiene

- [x] GitHub repo created (`ParcelPilotSupport`), **public**
- [x] `.gitignore` covers `.env`, `venv`, `node_modules`, `__pycache__`, `.chroma`, `*.db`
- [x] `.env.example` lists `OPENAI_API_KEY`, model name, snapshot override
- [x] Source PDFs + xlsx live under `data/source/` (tracked)
- [x] README: what it is, personas, how to run locally, how to run tests
- [x] Incremental commits pushed per `PLAN.md` slices (not one dump)

---

## B. Data plane

- [x] xlsx → SQLite: `accounts`, `orders`, `tickets`
- [x] Snapshot clock frozen at `2026-08-16 11:00 Asia/Kolkata`
- [x] Generated `escalations`, `ticket_updates`, `tasks`, `audit_log` tables
- [x] Boot logs row counts (4 / 6 / 7)
- [x] Tests: seed integrity (IDs ORD-1001… ORD-4001, TKT-450…505)

---

## C. Policy calculators (must be unit-tested)

Cancellation:

- [x] ORD-1001 → allowed, fee **0**, basis includes Northstar agreement
- [x] ORD-1002 → not allowed, RTO
- [x] ORD-2001 → allowed, fee **250**
- [x] ORD-3001 → allowed, fee **0** (within 30 min)
- [x] ORD-4001 → not allowed (DELIVERED)
- [x] DRAFT path covered (even if unused in xlsx)
- [x] Calculator does **not** special-case order IDs; uses status + account contract + times

Service credit:

- [x] ORD-2002 → eligible, amount **300** (LumenWorks >4h fixed)
- [x] Default formula min(500, 10% fee) used when no LumenWorks clause
- [x] Unknown carrier fault → no promise, `uncertain`
- [x] Customer fault → ineligible
- [x] Amount > 1000 → manager approval flag
- [x] Northstar monthly cap 5000 considered

SLA / severity:

- [x] TKT-501 → P1, Northstar 15 min, **breached** at snapshot
- [x] TKT-505 → P1 security, Enterprise 30 min, **breached**
- [x] TKT-502 → P2 (workaround exists), Growth 4 business hours, not necessarily breached
- [x] TKT-503 → P3
- [x] Axis Labs uses v3 Enterprise targets (no custom agreement)
- [x] v2 targets never used in calculator

---

## D. Access control

- [x] Customer header requires `account_id`
- [x] Customer ACCT-001 cannot load ORD-2001 / TKT-502 / LumenWorks agreement
- [x] Cross-tenant miss returns **NotFound**, not 403 with existence leak
- [x] Staff can load all accounts
- [x] Document search for customer excludes other agreements
- [x] ACL in repositories; prompt is not the enforcement layer
- [ ] Confirm-action re-checks ACL

---

## E. Documents and retrieval

- [x] All six PDFs ingested with metadata (`status`, `authority`, `account_id`, `effective_from`)
- [x] v2 `deprecated`, authority 0, excluded from default search
- [x] Agreements authority 100, bound to ACCT-001 / ACCT-002
- [x] Chunks cite filename back to the UI
- [x] Query about current Enterprise P1 does not treat v2 “1 hour” as current policy
- [x] Historical ticket text is not in the policy index (tickets stay in SQL)

---

## F. Agent tools (minimum three classes)

- [x] `search_documents`
- [x] Structured lookup (`get_order` / `get_ticket` / `get_account` / lists)
- [x] Structured calculate (`assess_cancellation` / `assess_failed_pickup_credit` / `classify_severity_and_sla`)
- [x] State-changing **propose** tools (escalation, ticket update, task) — at least one wired, three preferred
- [x] Tools return structured errors (`not_found`, `forbidden` never for customers — use not_found)
- [x] Agent can chain: order → account → agreement → SOP → calculate → propose

---

## G. Confirmation before actions

- [x] Propose does not write business tables
- [x] UI shows payload and asks Confirm / Cancel
- [ ] Confirm is the only writer
- [ ] Cancel drops proposal
- [x] Replay confirm is idempotent
- [ ] Demo: escalate TKT-505 or cancel-request follow-up on ORD-1001

---

## H. Chat agent behaviour

- [ ] Natural language in, grounded language out
- [ ] Uses snapshot time for “now”
- [ ] Cites files / record IDs
- [ ] Mentions TKT-450 as **wrong history** on Northstar cancel-fee questions
- [ ] Mentions TKT-451 as **wrong** vs 5,000 row limit + KI-208
- [ ] KI-211 warning on SwiftShip BOOKED lag (TKT-504 / ORD-1001 as relevant)
- [ ] TKT-503 → escalate, no invented billing-contact SOP
- [ ] Unknown credit fault → no promised rupees
- [ ] SSE/tool timeline visible in UI
- [ ] Does not hard-code example answers by order ID in prompts

---

## I. Dual context + UI

- [ ] Persona switcher: 4 customers + staff roles
- [ ] Customer chat vs internal chat clearly labelled
- [ ] Tool-in-use indicator
- [ ] Citation chips
- [ ] Confirmation card
- [ ] Ops Pulse page for staff
- [ ] Active account chip always visible

---

## J. Ops Pulse (proactive)

- [ ] Detector: P1 SLA breach (TKT-501, TKT-505)
- [ ] Detector: security exposure (TKT-505)
- [ ] Detector: KI-208 / bulk CSV cluster (TKT-502, TKT-451)
- [ ] Detector: SwiftShip status lag (TKT-504, KI-211)
- [ ] Detector: failed pickup ORD-2002
- [ ] Staff tool or page can list these without a custom prompt
- [ ] Evidence IDs clickable or copyable into chat

---

## K. Tests to keep green

- [ ] Calculator gold table
- [ ] ACL isolation
- [ ] Retrieval filter on deprecated
- [ ] Confirm/cancel action store
- [ ] Pulse detectors on frozen snapshot
- [ ] `GET /health`

---

## L. Hosting and submission

- [ ] Hosted UI URL works without local setup
- [ ] API reachable from that UI
- [ ] README run instructions accurate on a clean machine
- [ ] ~5 min demo video: architecture, live demo, decisions
- [ ] Architecture note (short): agent, tools, docs vs SQL, reliability, trade-offs
- [ ] Product note: extra problems, what we’d build next (prioritised), what we cut, **one metric**
- [ ] AI coding tools used (Cursor, etc.) stated honestly
- [ ] Public repo link
- [ ] Google Form submitted: https://forms.gle/hLGBrDrNRmK7UAbv6

---

## M. Demo script beats (video)

- [ ] Architecture diagram (≤1 min)
- [ ] Northstar ORD-1001: no fee + conflict with TKT-450 + confirm
- [ ] LumenWorks ORD-2002: ₹300 not default ₹240
- [ ] Switch persona: cannot see the other account’s order
- [ ] Ops Pulse: TKT-505 / TKT-501 red
- [ ] TKT-502: known issue not “plan only supports 3000”
- [ ] Confirmation refused / cancelled once to show the gate
- [ ] Close on trade-off: calculators in code vs LLM math

---

## N. Intentionally out of scope (do not start)

- [x] Real SSO
- [x] Live carrier APIs
- [x] Fine-tuning
- [x] Full return-to-origin operations product
- [x] Using deprecated v2 as current policy

---

## Slice tracker (push after each)

| Slice | Commit theme | Pushed |
|---|---|---|
| 0 | Repo skeleton + docs + source pack | [x] |
| 1 | SQLite load + health | [x] |
| 2 | Calculators + gold tests | [x] |
| 3 | Tenant ACL | [x] |
| 4 | Doc ingest + ranked retrieval | [x] |
| 5 | Read tools | [ ] |
| 6 | Propose + confirm actions | [ ] |
| 7 | LangGraph agent + SSE | [ ] |
| 8 | Chat UI | [ ] |
| 9 | Ops Pulse | [ ] |
| 10 | Citations / conflicts polish | [ ] |
| 11 | Hosting | [ ] |
| 12 | Submission notes + demo script | [ ] |
