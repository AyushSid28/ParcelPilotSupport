from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta

from app.auth import NotFound, visible_account
from app.clock import now
from app.models import Actor


def propose(conn, actor: Actor, action_type: str, payload: dict) -> dict:
    proposal_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO proposals (id, actor_kind, account_id, staff_id, action_type, payload, status, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (
            proposal_id,
            actor.kind,
            actor.account_id,
            actor.staff_id,
            action_type,
            json.dumps(payload),
            "pending",
            now().isoformat(),
        ),
    )
    conn.commit()
    return {"proposal_id": proposal_id, "action_type": action_type, "payload": payload, "status": "pending"}


def _row(conn, proposal_id: str):
    row = conn.execute("SELECT * FROM proposals WHERE id=?", (proposal_id,)).fetchone()
    if not row:
        raise NotFound()
    return row


def confirm(conn, actor: Actor, proposal_id: str) -> dict:
    row = _row(conn, proposal_id)
    if row["status"] == "confirmed":
        return {"proposal_id": proposal_id, "status": "confirmed", "idempotent": True}
    if row["status"] != "pending":
        raise ValueError("proposal is not pending")
    stored = datetime.fromisoformat(row["created_at"])
    if now() - stored > timedelta(minutes=10):
        raise ValueError("proposal expired")

    payload = json.loads(row["payload"])
    account_id = payload.get("account_id") or row["account_id"]
    if account_id and not visible_account(actor, account_id):
        raise NotFound()

    writer = actor.staff_id or actor.account_id or "unknown"
    stamp = now().isoformat()
    action_id = str(uuid.uuid4())
    kind = row["action_type"]

    if kind == "escalation":
        conn.execute(
            """INSERT INTO escalations VALUES (?,?,?,?,?,?,?)""",
            (
                action_id,
                payload.get("ticket_id"),
                account_id,
                payload.get("reason", ""),
                payload.get("priority", "P2"),
                writer,
                stamp,
            ),
        )
    elif kind == "ticket_update":
        conn.execute(
            """INSERT INTO ticket_updates VALUES (?,?,?,?,?,?)""",
            (
                action_id,
                payload["ticket_id"],
                payload.get("note", ""),
                payload.get("new_status"),
                writer,
                stamp,
            ),
        )
    elif kind == "task":
        conn.execute(
            """INSERT INTO tasks VALUES (?,?,?,?,?,?)""",
            (
                action_id,
                payload.get("title", "Follow-up"),
                account_id,
                payload.get("related_id"),
                writer,
                stamp,
            ),
        )
    else:
        raise ValueError(f"unknown action {kind}")

    conn.execute("UPDATE proposals SET status='confirmed' WHERE id=?", (proposal_id,))
    conn.execute(
        "INSERT INTO audit_log (at, actor, event, detail) VALUES (?,?,?,?)",
        (stamp, writer, "confirm", json.dumps({"proposal_id": proposal_id, "action_id": action_id})),
    )
    conn.commit()
    return {"proposal_id": proposal_id, "status": "confirmed", "action_id": action_id, "action_type": kind}


def cancel(conn, actor: Actor, proposal_id: str) -> dict:
    row = _row(conn, proposal_id)
    payload = json.loads(row["payload"])
    account_id = payload.get("account_id") or row["account_id"]
    if account_id and not visible_account(actor, account_id):
        raise NotFound()
    conn.execute("UPDATE proposals SET status='cancelled' WHERE id=?", (proposal_id,))
    conn.commit()
    return {"proposal_id": proposal_id, "status": "cancelled"}
