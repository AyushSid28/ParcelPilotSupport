# ParcelPilot Support Copilot

ParcelPilot Support Copilot is a small grounded support app for a deliberately messy customer-support pack. It handles customer questions about orders, cancellations, pickup credits, and ticket SLAs while keeping customer data isolated and requiring confirmation before any action is queued.

Live demo: [https://parcelpilotsupport.onrender.com](https://parcelpilotsupport.onrender.com)

Public repo: [https://github.com/AyushSid28/ParcelPilotSupport](https://github.com/AyushSid28/ParcelPilotSupport)

The assessment clock is fixed at **2026-08-16 11:00 Asia/Kolkata**, so SLA and pickup-delay answers are reproducible.

## What It Does

- Customers can ask about their own orders and tickets.
- Staff can see cross-account support context and use Ops Pulse.
- Cancellation fees, pickup credits, and SLA breaches are calculated in code.
- Signed customer agreements override the generic SOP when they conflict.
- Old tickets are treated as historical context, not policy authority.
- Escalations and follow-up tasks are only queued after the user clicks Confirm.

## Try It

Open the [hosted demo](https://parcelpilotsupport.onrender.com) and use the persona dropdown.

Render's free tier sleeps when idle, so the first load can take about a minute.

Good demo paths:

- Northstar: ask whether `ORD-1001` can be cancelled without a fee.
- LumenWorks: ask about the missed-pickup credit for `ORD-2002`.
- Staff: open Ops Pulse and inspect `TKT-505` or `TKT-501`.
- LumenWorks: ask about `TKT-502` and the bulk CSV limit.

## Run from source

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e "./backend[dev]"
cp .env.example .env   # set GROQ_API_KEY
make test
make api               # http://127.0.0.1:8000/health
```

In another terminal:

```bash
npm --prefix web install
npm --prefix web run dev   # http://127.0.0.1:5173
```

The app uses the persona dropdown instead of real login. Customers only see their own account data; staff personas can see the broader queue.

## Docker (optional, local only)

Docker is included for local testing. The public demo is hosted as a Python service on Render.

```bash
docker build -t parcelpilot .
docker run -p 8000:8000 -e GROQ_API_KEY=... parcelpilot
```

Then open http://127.0.0.1:8000

## Deployment

The hosted demo is deployed on Render as a Python web service.

Build command:

```bash
bash scripts/render-build.sh
```

Start command:

```bash
bash scripts/render-start.sh
```

Required environment variable:

```bash
GROQ_API_KEY=...
```

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Product note](docs/PRODUCT_NOTE.md)
