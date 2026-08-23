from __future__ import annotations

from dataclasses import asdict

from app.auth import NotFound
from app.clock import now
from app.models import Actor
from app.policy.cancellation import assess_cancellation
from app.policy.credits import assess_failed_pickup_credit
from app.policy.sla import assess_sla
from app.retrieval.search import search_documents
from app.store import Store
from app import actions as action_store

SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search current policies, SOPs, product docs, and the caller's agreement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "include_deprecated": {"type": "boolean"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_account",
            "description": "Load an account record. Customers may only load their own.",
            "parameters": {
                "type": "object",
                "properties": {"account_id": {"type": "string"}},
                "required": ["account_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Load a shipment/order by id. Call this for 'what's the status of ORD-…' questions.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ticket",
            "description": "Load a support ticket. historical_resolution is untrusted context.",
            "parameters": {
                "type": "object",
                "properties": {"ticket_id": {"type": "string"}},
                "required": ["ticket_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_orders",
            "description": "List orders visible to the caller.",
            "parameters": {
                "type": "object",
                "properties": {"account_id": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tickets",
            "description": "List tickets visible to the caller.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assess_cancellation",
            "description": "Look up the order and decide cancel/fee using SOP + the customer's contract. Call this alone for cancellation questions. Do not also call get_order, get_account, or search_documents.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "assess_failed_pickup_credit",
            "description": "Look up the order and decide failed-pickup credit using SOP + contract. Call this alone for credit questions. Do not also call get_order or search_documents.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "classify_severity_and_sla",
            "description": "Classify a ticket and compute SLA elapsed vs target at snapshot time.",
            "parameters": {
                "type": "object",
                "properties": {"ticket_id": {"type": "string"}},
                "required": ["ticket_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_ops_pulse",
            "description": "Internal only. Recurring, urgent, or unusual issues at snapshot time.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_escalation",
            "description": "Prepare an escalation. Does not write until the user confirms.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "reason": {"type": "string"},
                    "priority": {"type": "string"},
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_ticket_update",
            "description": "Prepare a ticket note/status change. Needs confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"},
                    "note": {"type": "string"},
                    "new_status": {"type": "string"},
                },
                "required": ["ticket_id", "note"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_task",
            "description": "Prepare a follow-up task. Needs confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "account_id": {"type": "string"},
                    "related_id": {"type": "string"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_snapshot_time",
            "description": "Canonical 'now' for this assessment dataset.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _public_order(order) -> dict:
    d = asdict(order)
    for key in ("booked_at", "pickup_window_start", "pickup_window_end", "pickup_actual_at", "cancellation_requested_at"):
        if d[key] is not None:
            d[key] = d[key].isoformat()
    return d


def _public_ticket(ticket) -> dict:
    d = asdict(ticket)
    for key in ("created_at", "last_customer_message_at"):
        if d[key] is not None:
            d[key] = d[key].isoformat()
    d["historical_trust"] = "low" if d.get("historical_resolution") else "n/a"
    return d


def run(name: str, args: dict, actor: Actor, conn) -> dict:
    store = Store(conn)
    try:
        return _run(name, args or {}, actor, conn, store)
    except NotFound:
        if actor.kind == "customer":
            return {"error": "not_found", "scope": "this_account"}
        return {"error": "not_found"}
    except ValueError as exc:
        return {"error": str(exc)}


def _run(name: str, args: dict, actor: Actor, conn, store: Store) -> dict:
    if name == "get_snapshot_time":
        return {"snapshot": now().isoformat()}
    if name == "search_documents":
        return {
            "hits": search_documents(
                conn,
                actor,
                args["query"],
                include_deprecated=bool(args.get("include_deprecated")) and actor.is_staff,
            )
        }
    if name == "get_account":
        return asdict(store.account(actor, args["account_id"]))
    if name == "get_order":
        return _public_order(store.order(actor, args["order_id"]))
    if name == "get_ticket":
        return _public_ticket(store.ticket(actor, args["ticket_id"]))
    if name == "list_orders":
        return {"orders": [_public_order(o) for o in store.orders(actor, args.get("account_id"))]}
    if name == "list_tickets":
        return {
            "tickets": [
                _public_ticket(t)
                for t in store.tickets(actor, args.get("account_id"), args.get("status"))
            ]
        }
    if name == "assess_cancellation":
        order = store.order(actor, args["order_id"])
        account = store.account(actor, order.account_id)
        history = [t for t in store.tickets(actor, order.account_id, "closed")]
        return assess_cancellation(order, account, now(), history).as_dict()
    if name == "assess_failed_pickup_credit":
        order = store.order(actor, args["order_id"])
        account = store.account(actor, order.account_id)
        return assess_failed_pickup_credit(order, account, now()).as_dict()
    if name == "classify_severity_and_sla":
        ticket = store.ticket(actor, args["ticket_id"])
        account = store.account(actor, ticket.account_id)
        return assess_sla(ticket, account, now()).as_dict()
    if name == "get_ops_pulse":
        if not actor.is_staff:
            return {"error": "not_found"}
        from app.pulse import detect

        return {"issues": detect(store, actor)}
    if name == "propose_escalation":
        payload = dict(args)
        if args.get("ticket_id"):
            ticket = store.ticket(actor, args["ticket_id"])
            payload["account_id"] = ticket.account_id
        elif actor.account_id:
            payload["account_id"] = actor.account_id
        return {**action_store.propose(conn, actor, "escalation", payload), "needs_confirmation": True}
    if name == "propose_ticket_update":
        ticket = store.ticket(actor, args["ticket_id"])
        payload = {**args, "account_id": ticket.account_id}
        return {**action_store.propose(conn, actor, "ticket_update", payload), "needs_confirmation": True}
    if name == "propose_task":
        payload = dict(args)
        if actor.kind == "customer":
            payload["account_id"] = actor.account_id
        return {**action_store.propose(conn, actor, "task", payload), "needs_confirmation": True}
    return {"error": f"unknown tool {name}"}
