from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

ActorKind = Literal["customer", "staff"]
StaffRole = Literal["agent", "csm", "ops_lead"]


@dataclass(frozen=True)
class Actor:
    kind: ActorKind
    account_id: str | None = None
    staff_id: str | None = None
    role: StaffRole | None = None

    @property
    def is_staff(self) -> bool:
        return self.kind == "staff"


@dataclass(frozen=True)
class Account:
    account_id: str
    account_name: str
    plan: str
    status: str
    csm: str
    contract_file: str | None
    premium_support: bool
    notes: str


@dataclass(frozen=True)
class Order:
    order_id: str
    account_id: str
    carrier: str
    status: str
    booked_at: datetime
    pickup_window_start: datetime
    pickup_window_end: datetime
    pickup_actual_at: datetime | None
    shipment_fee_inr: float
    carrier_fault: bool | None
    customer_fault: bool | None
    cancellation_requested_at: datetime | None
    notes: str


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    account_id: str
    created_at: datetime
    status: str
    subject: str
    description: str
    channel: str
    assigned_to: str
    last_customer_message_at: datetime | None
    historical_resolution: str | None
