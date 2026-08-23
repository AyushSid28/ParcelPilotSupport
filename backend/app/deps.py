from fastapi import Header, HTTPException

from app.auth import parse_actor
from app.models import Actor


def actor_from_headers(
    x_actor_type: str | None = Header(default=None),
    x_account_id: str | None = Header(default=None),
    x_staff_id: str | None = Header(default=None),
    x_staff_role: str | None = Header(default=None),
) -> Actor:
    try:
        return parse_actor(x_actor_type, x_account_id, x_staff_id, x_staff_role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
