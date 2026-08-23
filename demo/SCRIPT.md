# Demo script (~5 minutes)

Clock on screen: 16 Aug 2026, 11:00 IST.

1. **Architecture (45s)** — Dual chat + Ops Pulse. Tools enforce ACL. Fees and SLA are Python, not the model. Docs ranked by authority; v2 is deprecated.

2. **Northstar customer, ORD-1001** — “Can we cancel without a fee?” Show `get_order` → `assess_cancellation`. Fee 0 because of the enterprise agreement. Mention TKT-450 was wrong. Confirm a follow-up task if one is proposed.

3. **Switch to LumenWorks** — Sidebar must not list ORD-1001. Ask about ORD-2002 credit. Answer is ₹300 (contract), not min(500, 10% of 2400)=₹240. Ask ORD-2001 cancel: ₹250.

4. **Staff / Ops Pulse** — Red cards for TKT-505 and TKT-501. Open TKT-505 in chat: P1, 30-minute Enterprise target, already breached, propose escalation, **cancel once**, then confirm.

5. **TKT-502** — 4,200-row CSV. Product limit 5,000. KI-208 workaround. Do not repeat TKT-451 “Growth only supports 3,000”.

6. **Close** — Calculators in code; confirm gate; pulse without a prompt. Metric: unsafe-action rate.

## AI tools used

Cursor (Grok) for scaffolding and tests. Policy numbers were taken from the PDFs and pinned in `backend/tests/test_policy.py`, not accepted from the model.
