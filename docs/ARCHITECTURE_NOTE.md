# Architecture note

ParcelPilot Support Copilot is a dual-context support agent over a small, conflicting corpus. The interesting work is not the chat loop.

## Agent

A bounded OpenAI tool loop (max 8 rounds) over SSE. We did not wrap it in LangGraph: the graph would be linear (call tools until text). The policy lives in tools, not in graph nodes.

## Tools

Read tools hit SQLite through an ACL store. `assess_cancellation`, `assess_failed_pickup_credit`, and `classify_severity_and_sla` are pure functions with gold tests. Propose tools insert a pending row only. Confirm is a separate HTTP call.

## Documents vs structured data

Six PDFs are chunked with authority metadata. Search is lexical overlap multiplied by authority, with deprecated v2 filtered out unless a staff user asks. Tickets and orders stay in SQL so historical resolutions cannot pollute the policy index.

## Reliability

Source order is coded: agreement > current SOP/policy/product > known issues > untrusted tickets. Calculators emit `conflicts` (TKT-450 vs Northstar waiver). Unknown carrier fault returns `uncertain` instead of a rupee amount. Missing procedures (billing contact) have no tool that invents a SOP.

## Trade-offs

- Lexical retrieval instead of embeddings: the corpus is a handful of short PDFs; a vector database would add a key and still need the same authority filter.
- Frozen snapshot clock: matches the pack. A production clock is one config change.
- Mocked auth headers: real SSO is out of scope; isolation is still enforced in the store.
- Single Docker process serving API + built UI: one URL for the demo.
