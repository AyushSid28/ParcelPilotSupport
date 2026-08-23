# ParcelPilot Support Copilot

Grounded support copilot for ParcelPilot — tenant-scoped tools, contract-aware policy, and an internal ops pulse.

Public repo: https://github.com/AyushSid28/ParcelPilotSupport

Clock for every time question: **2026-08-16 11:00 Asia/Kolkata**.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e "./backend[dev]"
cp .env.example .env   # set OPENAI_API_KEY
make test
make api               # http://127.0.0.1:8000/health
```

In another terminal:

```bash
npm --prefix web install
npm --prefix web run dev   # http://127.0.0.1:5173
```

Personas are a dropdown. Customers only see their orders. Staff see Ops Pulse.

Docker:

```bash
docker build -t parcelpilot .
docker run -p 8000:8000 -e OPENAI_API_KEY=... parcelpilot
```

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
