# ParcelPilot Support Copilot

Grounded support copilot for [ParcelPilot](https://github.com/AyushSid28/ParcelPilotSupport) — tenant-scoped tools, contract-aware policy, and an internal ops pulse.

This is a take-home system for CalQuity: a **customer** chatbot and an **internal ops** chatbot over an intentionally messy policy pack (current vs deprecated policy, customer contracts that override SOP, historical tickets that can be wrong), plus **Ops Pulse** for proactive issue detection.

## Status

Slice 0: repository skeleton, architecture, and source pack only. The API and UI are not in this commit.

Design docs:

- [Architecture](docs/ARCHITECTURE.md)
- [Build plan](docs/PLAN.md)
- [Checklist](docs/CHECKLIST.md)

## Source pack

Assessment documents live in `data/source/`:

- Support Policy v3 (current) and v2 (deprecated)
- Cancellation & Service Credit SOP v4
- Product operations guide and known issues
- Northstar and LumenWorks agreements
- `ParcelPilot_Assessment_Data.xlsx` (accounts, orders, tickets)

**System clock for all time questions:** `2026-08-16 11:00 Asia/Kolkata`

## Personas (planned)

Customers: Northstar Logistics, LumenWorks, Beacon Retail, Axis Labs  
Staff: agent, CSM, ops lead (mocked headers; ACL enforced in the data layer)

## Local run

Not applicable until later slices. Planned:

```bash
cp .env.example .env   # add OPENAI_API_KEY
make dev               # API :8000 + web :3000
```

## Repository

Public GitHub: https://github.com/AyushSid28/ParcelPilotSupport
