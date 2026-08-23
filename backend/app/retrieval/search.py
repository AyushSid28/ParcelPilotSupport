from __future__ import annotations

import re

from app.models import Actor

TOKEN = re.compile(r"[a-z0-9]{2,}")


def _tokens(text: str) -> set[str]:
    return set(TOKEN.findall(text.lower()))


def _allowed(actor: Actor, row, include_deprecated: bool) -> bool:
    if row["status"] == "deprecated" and not include_deprecated:
        return False
    if row["account_id"] and actor.kind == "customer" and row["account_id"] != actor.account_id:
        return False
    if row["doc_type"] == "agreement" and actor.kind == "customer" and row["account_id"] != actor.account_id:
        return False
    return True


def search_documents(
    conn,
    actor: Actor,
    query: str,
    *,
    include_deprecated: bool = False,
    limit: int = 6,
) -> list[dict]:
    q = _tokens(query)
    scored: list[tuple[float, dict]] = []
    for row in conn.execute("SELECT * FROM doc_chunks"):
        if not _allowed(actor, row, include_deprecated):
            continue
        overlap = len(q & _tokens(row["heading"] + " " + row["body"]))
        if overlap == 0:
            continue
        score = overlap * (1 + row["authority"] / 50)
        scored.append(
            (
                score,
                {
                    "filename": row["filename"],
                    "title": row["title"],
                    "status": row["status"],
                    "authority": row["authority"],
                    "account_id": row["account_id"],
                    "heading": row["heading"],
                    "snippet": row["body"][:500],
                    "score": round(score, 2),
                },
            )
        )
    scored.sort(key=lambda x: (-x[0], -x[1]["authority"]))
    return [item for _, item in scored[:limit]]
