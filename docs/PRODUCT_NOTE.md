# Product note

## Extra problems

**Trust (core path).** Answers are grounded in ranked documents and Python policy math. The UI shows which tool ran and asks before any write. Past tickets are labelled untrusted; TKT-450 and TKT-451 are called out when they contradict current rules.

**Proactive detection (Ops Pulse).** Staff get a page of detectors at snapshot time: P1 SLA breaches (TKT-501, TKT-505), credential exposure, KI-208 bulk-CSV cluster, SwiftShip status lag, failed pickup ORD-2002. Detectors do not need the LLM.

## What we would build next

1. **Human QA queue** for `must_escalate` and manager-approval credits — adoption dies if the bot is confidently wrong, so a sampled review loop matters first.
2. **Carrier status verify** for KI-211 instead of a 20-minute wait heuristic.
3. **Contract parser on ingest** so a new PDF agreement does not require a `contracts.py` edit.
4. **Customer-visible SLA countdown** on open P1s, using the same calculator ops already see.

## Left out on purpose

SSO, live carrier APIs, a real ticketing backend, fine-tuning, and a full return-to-origin workflow. The pack is four accounts and a frozen clock; those systems would fake depth.

## One metric

**Unsafe-action rate = 0**, then **correct-and-grounded resolution rate**: sampled chats where a reviewer agrees the calculator verdict was applied and a current authoritative file was cited. Reopen-in-48h is the lagging companion metric.
