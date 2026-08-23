from dataclasses import dataclass, field

from app.models import Account, Order, Ticket
from app.policy.contracts import for_account
from app.policy.timeutil import hours_between, minutes_between

SOP = "03_Cancellation_and_Service_Credit_SOP_v4.pdf"
PRODUCT = "04_Product_Operations_Guide_and_Known_Issues.pdf"
FREE_WINDOW_MIN = 30
DEFAULT_FEE = 250.0


@dataclass
class CancellationVerdict:
    allowed: bool
    fee_inr: float
    reason_codes: list[str]
    policy_basis: list[str]
    conflicts: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_step: str | None = None
    requires_confirmation: bool = True

    def as_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "fee_inr": self.fee_inr,
            "reason_codes": self.reason_codes,
            "policy_basis": self.policy_basis,
            "conflicts": self.conflicts,
            "warnings": self.warnings,
            "next_step": self.next_step,
            "requires_confirmation": self.requires_confirmation and self.allowed,
        }


def assess_cancellation(
    order: Order,
    account: Account,
    now,
    historical_tickets: list[Ticket] | None = None,
) -> CancellationVerdict:
    contract = for_account(account)
    basis = [SOP]
    if contract.agreement_file:
        basis.insert(0, contract.agreement_file)

    if order.status == "DELIVERED":
        return CancellationVerdict(
            False, 0, ["STATUS_DELIVERED"], basis, next_step="cannot_cancel", requires_confirmation=False
        )
    if order.status == "PICKED_UP":
        return CancellationVerdict(
            False,
            0,
            ["STATUS_PICKED_UP"],
            basis + [PRODUCT],
            next_step="return_to_origin",
            requires_confirmation=False,
        )
    if order.status == "DRAFT":
        return CancellationVerdict(True, 0, ["STATUS_DRAFT"], basis)

    if order.status != "BOOKED":
        return CancellationVerdict(
            False, 0, ["STATUS_UNKNOWN"], basis, next_step="escalate", requires_confirmation=False
        )

    codes = ["STATUS_BOOKED"]
    warnings: list[str] = []
    if order.carrier == "SwiftShip" and order.pickup_window_start <= now and order.pickup_actual_at is None:
        warnings.append("KI-211: SwiftShip pickup webhooks can lag up to 20 minutes.")
        basis = list(dict.fromkeys(basis + [PRODUCT]))

    if contract.cancel_booked_pre_pickup_fee == 0:
        fee = 0.0
        codes.append("CONTRACT_WAIVES_FEE")
    else:
        requested = order.cancellation_requested_at or now
        waited = minutes_between(order.booked_at, requested)
        if waited <= FREE_WINDOW_MIN:
            fee = 0.0
            codes.append("WITHIN_FREE_WINDOW")
        else:
            fee = DEFAULT_FEE
            codes.append("SOP_CANCELLATION_FEE")

    conflicts = []
    for ticket in historical_tickets or []:
        text = ticket.historical_resolution or ""
        if fee == 0 and "250" in text:
            conflicts.append(
                {
                    "ignored": ticket.ticket_id,
                    "why": "historical_ticket_not_authority",
                    "said": text,
                }
            )

    return CancellationVerdict(True, fee, codes, basis, conflicts=conflicts, warnings=warnings)
