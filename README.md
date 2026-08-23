# ParcelPilot Support Copilot

Grounded support copilot for ParcelPilot — tenant-scoped tools, contract-aware policy, and an internal ops pulse.

Public repo: https://github.com/AyushSid28/ParcelPilotSupport

Clock for every time question: **2026-08-16 11:00 Asia/Kolkata**.

## Try the hosted demo

No clone, no Docker. Open [https://parcelpilotsupport.onrender.com](https://parcelpilotsupport.onrender.com) and use the persona dropdown.

Free Render sleeps when idle; the first load after a nap can take about a minute.

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

Personas are a dropdown. Customers only see their orders. Staff see Ops Pulse.

## Docker (optional, local only)

For anyone who wants a single container after cloning. This is **not** how the public demo is hosted.

```bash
docker build -t parcelpilot .
docker run -p 8000:8000 -e GROQ_API_KEY=... parcelpilot
```

Then open http://127.0.0.1:8000

## Deploy the public URL (maintainers)

Host on Render as a **Python** web service, not a Docker runtime. Testers never need Docker.

1. [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint** (this `render.yaml`) or **Web Service** on `AyushSid28/ParcelPilotSupport`.
2. Runtime **Python**. Build `bash scripts/render-build.sh`. Start `bash scripts/render-start.sh`. Health `/health`.
3. Env: `GROQ_API_KEY` from local `.env`. Optional `GROQ_MODEL=openai/gpt-oss-120b`.
4. Live URL: [https://parcelpilotsupport.onrender.com](https://parcelpilotsupport.onrender.com)

Free instances sleep when idle; the first request after a nap can take a minute.

## What to try

- Northstar: cancel ORD-1001 (should be free; ignore TKT-450)
- LumenWorks: credit on ORD-2002 (₹300, not ₹240)
- Staff pulse: TKT-505 and TKT-501 SLA breaches
- TKT-502: KI-208, not a 3,000-row plan cap

## Docs

- [Architecture](docs/ARCHITECTURE.md)
- [Architecture note](docs/ARCHITECTURE_NOTE.md)
- [Product note](docs/PRODUCT_NOTE.md)
- [Demo script](demo/SCRIPT.md)
