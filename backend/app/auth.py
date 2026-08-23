from __future__ import annotations

from dataclasses import dataclass

from app.models import Actor


class NotFound(Exception):
    pass


def parse_actor(
    actor_type: str | None,
    account_id: str | None,
    staff_id: str | None,
    role: str | None,
) -> Actor:
    kind = (actor_type or "").strip().lower()
    if kind == "customer":
        if not account_id:
            raise ValueError("customer context requires X-Account-Id")
        return Actor(kind="customer", account_id=account_id)
    if kind == "staff":
        if role not in {"agent", "csm", "ops_lead"}:
            raise ValueError("staff context requires X-Staff-Role")
        return Actor(kind="staff", staff_id=staff_id, role=role)  # type: ignore[arg-type]
    raise ValueError("X-Actor-Type must be customer or staff")


def visible_account(actor: Actor, account_id: str) -> bool:
    if actor.is_staff:
        return True
    return actor.account_id == account_id
