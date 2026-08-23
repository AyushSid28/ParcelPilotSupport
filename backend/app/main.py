from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.clock import SNAPSHOT
from app.config import settings
from app.db import connect, rebuild
from app.paths import WEB_DIST
from app.retrieval.ingest import persist


@asynccontextmanager
async def lifespan(_app: FastAPI):
    conn = rebuild()
    persist(conn)
    conn.close()
    yield


app = FastAPI(title="ParcelPilot Support Copilot", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.get("/health")
def health() -> dict:
    conn = connect()
    try:
        accounts = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        tickets = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        chunks = conn.execute("SELECT COUNT(*) FROM doc_chunks").fetchone()[0]
    finally:
        conn.close()
    return {
        "ok": True,
        "snapshot": SNAPSHOT.isoformat(),
        "accounts": accounts,
        "orders": orders,
        "tickets": tickets,
        "chunks": chunks,
        "llm": settings.llm_provider,
        "model": settings.llm_model,
    }


if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="ui")
