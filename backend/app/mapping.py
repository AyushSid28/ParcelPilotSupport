from __future__ import annotations

from datetime import datetime

from app.models import Account, Order, Ticket


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


def _bool(value) -> bool | None:
    if value is None:
        return None
    return bool(value)


def account_from_row(row) -> Account:
    return Account(
        account_id=row["account_id"],
        account_name=row["account_name"],
        plan=row["plan"],
        status=row["status"],
        csm=row["csm"],
        contract_file=row["contract_file"],
        premium_support=bool(row["premium_support"]),
        notes=row["notes"],
    )


def order_from_row(row) -> Order:
    return Order(
        order_id=row["order_id"],
        account_id=row["account_id"],
        carrier=row["carrier"],
        status=row["status"],
        booked_at=_dt(row["booked_at"]),
        pickup_window_start=_dt(row["pickup_window_start"]),
        pickup_window_end=_dt(row["pickup_window_end"]),
        pickup_actual_at=_dt(row["pickup_actual_at"]),
        shipment_fee_inr=row["shipment_fee_inr"],
        carrier_fault=_bool(row["carrier_fault"]),
        customer_fault=_bool(row["customer_fault"]),
        cancellation_requested_at=_dt(row["cancellation_requested_at"]),
        notes=row["notes"],
    )


def ticket_from_row(row) -> Ticket:
    return Ticket(
        ticket_id=row["ticket_id"],
        account_id=row["account_id"],
        created_at=_dt(row["created_at"]),
        status=row["status"],
        subject=row["subject"],
        description=row["description"],
        channel=row["channel"],
        assigned_to=row["assigned_to"],
        last_customer_message_at=_dt(row["last_customer_message_at"]),
        historical_resolution=row["historical_resolution"],
    )
