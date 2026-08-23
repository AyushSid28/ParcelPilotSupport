from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from app.paths import SOURCE_DIR

CATALOG = [
    {
        "doc_id": "policy_v3",
        "filename": "01_Support_Policy_v3_CURRENT.pdf",
        "title": "Support Policy v3",
        "doc_type": "support_policy",
        "status": "current",
        "authority": 80,
        "account_id": None,
    },
    {
        "doc_id": "policy_v2",
        "filename": "02_Support_Policy_v2_DEPRECATED.pdf",
        "title": "Support Policy v2",
        "doc_type": "support_policy",
        "status": "deprecated",
        "authority": 0,
        "account_id": None,
    },
    {
        "doc_id": "sop_v4",
        "filename": "03_Cancellation_and_Service_Credit_SOP_v4.pdf",
        "title": "Cancellation & Service Credit SOP v4",
        "doc_type": "sop",
        "status": "current",
        "authority": 80,
        "account_id": None,
    },
    {
        "doc_id": "product_ops",
        "filename": "04_Product_Operations_Guide_and_Known_Issues.pdf",
        "title": "Product Operations Guide",
        "doc_type": "product",
        "status": "current",
        "authority": 70,
        "account_id": None,
    },
    {
        "doc_id": "northstar",
        "filename": "05_Northstar_Logistics_Enterprise_Agreement.pdf",
        "title": "Northstar Logistics Enterprise Agreement",
        "doc_type": "agreement",
        "status": "current",
        "authority": 100,
        "account_id": "ACCT-001",
    },
    {
        "doc_id": "lumenworks",
        "filename": "06_LumenWorks_Service_Agreement.pdf",
        "title": "LumenWorks Service Agreement",
        "doc_type": "agreement",
        "status": "current",
        "authority": 100,
        "account_id": "ACCT-002",
    },
]


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    filename: str
    title: str
    doc_type: str
    status: str
    authority: int
    account_id: str | None
    heading: str
    body: str


def _paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in text.replace("\r", "").split("\n\n")]
    chunks: list[str] = []
    buf = ""
    for part in parts:
        clean = " ".join(line.strip() for line in part.splitlines() if line.strip())
        if not clean:
            continue
        if len(buf) + len(clean) < 700:
            buf = f"{buf}\n{clean}".strip()
        else:
            if buf:
                chunks.append(buf)
            buf = clean
    if buf:
        chunks.append(buf)
    return chunks


def load_chunks(source: Path | None = None) -> list[Chunk]:
    root = source or SOURCE_DIR
    out: list[Chunk] = []
    for meta in CATALOG:
        reader = PdfReader(str(root / meta["filename"]))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        for body in _paragraphs(text):
            heading = body.split("\n", 1)[0][:120]
            out.append(Chunk(heading=heading, body=body, **meta))
    return out


def persist(conn, chunks: list[Chunk] | None = None) -> int:
    conn.execute("DELETE FROM doc_chunks")
    rows = chunks or load_chunks()
    for ch in rows:
        conn.execute(
            """INSERT INTO doc_chunks
               (doc_id, filename, title, doc_type, status, authority, account_id, heading, body)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                ch.doc_id,
                ch.filename,
                ch.title,
                ch.doc_type,
                ch.status,
                ch.authority,
                ch.account_id,
                ch.heading,
                ch.body,
            ),
        )
    conn.commit()
    return len(rows)
