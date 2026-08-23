from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.clock import SNAPSHOT
from app.config import settings
from app.db import connect, rebuild

app = FastAPI(title="ParcelPilot Support Copilot", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    conn = rebuild()
    from app.retrieval.ingest import persist

    persist(conn)
    conn.close()


@app.get("/health")
def health() -> dict:
    conn = connect()
    try:
        accounts = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        tickets = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    finally:
        conn.close()
    return {
        "ok": True,
        "snapshot": SNAPSHOT.isoformat(),
        "accounts": accounts,
        "orders": orders,
        "tickets": tickets,
    }
