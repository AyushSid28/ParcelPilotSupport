from __future__ import annotations

from dataclasses import dataclass

from app.models import Account

NORTHSTAR = "ACCT-001"
LUMENWORKS = "ACCT-002"


@dataclass(frozen=True)
class SlaTarget:
    minutes: int
    clock: str  # wall | business
    around_the_clock: bool


@dataclass(frozen=True)
class Contract:
    cancel_booked_pre_pickup_fee: float | None  # None = use SOP; 0 = waived
    failed_pickup_hours: float | None
    failed_pickup_amount: float | None
    credit_monthly_cap: float | None
    p1: SlaTarget
    p2: SlaTarget
    p3: SlaTarget
    weekend_coverage: bool
    agreement_file: str | None


def _v3(plan: str) -> Contract:
    if plan == "Enterprise":
        return Contract(
            cancel_booked_pre_pickup_fee=None,
            failed_pickup_hours=None,
            failed_pickup_amount=None,
            credit_monthly_cap=None,
            p1=SlaTarget(30, "wall", True),
            p2=SlaTarget(120, "wall", False),
            p3=SlaTarget(8 * 60, "business", False),
            weekend_coverage=True,
            agreement_file=None,
        )
    if plan == "Growth":
        return Contract(
            cancel_booked_pre_pickup_fee=None,
            failed_pickup_hours=None,
            failed_pickup_amount=None,
            credit_monthly_cap=None,
            p1=SlaTarget(2 * 60, "business", False),
            p2=SlaTarget(4 * 60, "business", False),
            p3=SlaTarget(2 * 8 * 60, "business", False),
            weekend_coverage=False,
            agreement_file=None,
        )
    return Contract(
        cancel_booked_pre_pickup_fee=None,
        failed_pickup_hours=None,
        failed_pickup_amount=None,
        credit_monthly_cap=None,
        p1=SlaTarget(4 * 60, "business", False),
        p2=SlaTarget(8 * 60, "business", False),
        p3=SlaTarget(2 * 8 * 60, "business", False),
        weekend_coverage=False,
        agreement_file=None,
    )


def for_account(account: Account) -> Contract:
    base = _v3(account.plan)
    if account.account_id == NORTHSTAR:
        return Contract(
            cancel_booked_pre_pickup_fee=0,
            failed_pickup_hours=None,
            failed_pickup_amount=None,
            credit_monthly_cap=5000,
            p1=SlaTarget(15, "wall", True),
            p2=SlaTarget(60, "wall", False),
            p3=SlaTarget(8 * 60, "business", False),
            weekend_coverage=True,
            agreement_file="05_Northstar_Logistics_Enterprise_Agreement.pdf",
        )
    if account.account_id == LUMENWORKS:
        return Contract(
            cancel_booked_pre_pickup_fee=None,
            failed_pickup_hours=4,
            failed_pickup_amount=300,
            credit_monthly_cap=None,
            p1=SlaTarget(2 * 60, "business", False),
            p2=SlaTarget(4 * 60, "business", False),
            p3=SlaTarget(2 * 8 * 60, "business", False),
            weekend_coverage=False,
            agreement_file="06_LumenWorks_Service_Agreement.pdf",
        )
    return base
