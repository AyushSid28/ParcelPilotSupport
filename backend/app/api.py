from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from app.agent import iter_chat
from app.auth import NotFound
from app.clock import SNAPSHOT
from app.db import connect
from app.deps import actor_from_headers
from app.models import Actor
from app.pulse import detect
from app.store import Store
from app import actions as action_store
from app.tools import _public_order, _public_ticket

router = APIRouter()

PERSONAS = [
    {"id": "northstar", "label": "Northstar (customer)", "kind": "customer", "account_id": "ACCT-001"},
    {"id": "lumenworks", "label": "LumenWorks (customer)", "kind": "customer", "account_id": "ACCT-002"},
    {"id": "beacon", "label": "Beacon Retail (customer)", "kind": "customer", "account_id": "ACCT-003"},
    {"id": "axis", "label": "Axis Labs (customer)", "kind": "customer", "account_id": "ACCT-004"},
    {"id": "maya", "label": "Maya (agent)", "kind": "staff", "staff_id": "maya", "role": "agent"},
    {"id": "rohit", "label": "Rohit (agent)", "kind": "staff", "staff_id": "rohit", "role": "agent"},
    {"id": "priya", "label": "Priya (CSM)", "kind": "staff", "staff_id": "priya", "role": "csm"},
    {"id": "ops", "label": "Ops lead", "kind": "staff", "staff_id": "ops", "role": "ops_lead"},
]


class ChatIn(BaseModel):
    messages: list[dict]


@router.get("/personas")
def personas() -> dict:
    return {"personas": PERSONAS, "snapshot": SNAPSHOT.isoformat()}


@router.get("/me")
def me(actor: Actor = Depends(actor_from_headers)) -> dict:
    conn = connect()
    try:
        store = Store(conn)
        account = None
        if actor.account_id:
            account = store.account(actor, actor.account_id)
        return {
            "kind": actor.kind,
            "account_id": actor.account_id,
            "staff_id": actor.staff_id,
            "role": actor.role,
            "account": None if not account else {
                "account_id": account.account_id,
                "account_name": account.account_name,
                "plan": account.plan,
            },
        }
    finally:
        conn.close()


@router.get("/orders")
def orders(actor: Actor = Depends(actor_from_headers)) -> dict:
    conn = connect()
    try:
        return {"orders": [_public_order(o) for o in Store(conn).orders(actor)]}
    finally:
        conn.close()


@router.get("/tickets")
def tickets(actor: Actor = Depends(actor_from_headers)) -> dict:
    conn = connect()
    try:
        return {"tickets": [_public_ticket(t) for t in Store(conn).tickets(actor)]}
    finally:
        conn.close()


@router.get("/ops/pulse")
def pulse(actor: Actor = Depends(actor_from_headers)) -> dict:
    if not actor.is_staff:
        return {"issues": []}
    conn = connect()
    try:
        return {"issues": detect(Store(conn), actor)}
    finally:
        conn.close()


@router.post("/actions/{proposal_id}/confirm")
def confirm(proposal_id: str, actor: Actor = Depends(actor_from_headers)) -> dict:
    conn = connect()
    try:
        return action_store.confirm(conn, actor, proposal_id)
    except NotFound:
        return {"error": "not_found"}
    except ValueError as exc:
        return {"error": str(exc)}
    finally:
        conn.close()


@router.post("/actions/{proposal_id}/cancel")
def cancel_action(proposal_id: str, actor: Actor = Depends(actor_from_headers)) -> dict:
    conn = connect()
    try:
        return action_store.cancel(conn, actor, proposal_id)
    except NotFound:
        return {"error": "not_found"}
    finally:
        conn.close()


@router.post("/chat")
def chat(body: ChatIn, actor: Actor = Depends(actor_from_headers)):
    conn = connect()

    def events():
        try:
            for item in iter_chat(body.messages, actor, conn):
                yield f"event: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"
        finally:
            conn.close()

    return StreamingResponse(events(), media_type="text/event-stream")
