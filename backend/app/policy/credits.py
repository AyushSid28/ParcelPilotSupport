from dataclasses import dataclass, field

from app.models import Account, Order
from app.policy.contracts import for_account
from app.policy.timeutil import hours_between

SOP = "03_Cancellation_and_Service_Credit_SOP_v4.pdf"
DEFAULT_HOURS = 2.0
DEFAULT_CAP = 500.0
DEFAULT_PCT = 0.10
MANAGER_THRESHOLD = 1000.0


@dataclass
class CreditVerdict:
    eligible: bool
    amount_inr: float | None
    uncertain: bool
    reason_codes: list[str]
    policy_basis: list[str]
    hours_late: float | None
    requires_manager_approval: bool = False
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "eligible": self.eligible,
            "amount_inr": self.amount_inr,
            "uncertain": self.uncertain,
            "reason_codes": self.reason_codes,
            "policy_basis": self.policy_basis,
            "hours_late": self.hours_late,
            "requires_manager_approval": self.requires_manager_approval,
            "warnings": self.warnings,
        }


def assess_failed_pickup_credit(order: Order, account: Account, now) -> CreditVerdict:
    contract = for_account(account)
    basis = [SOP]
    if contract.agreement_file:
        basis.insert(0, contract.agreement_file)

    if order.customer_fault:
        return CreditVerdict(False, None, False, ["CUSTOMER_FAULT"], basis, None)
    if order.carrier_fault is None:
        return CreditVerdict(False, None, True, ["CARRIER_FAULT_UNKNOWN"], basis, None)
    if order.carrier_fault is False:
        return CreditVerdict(False, None, False, ["CARRIER_NOT_AT_FAULT"], basis, None)

    pickup = order.pickup_actual_at or now
    hours_late = hours_between(order.pickup_window_end, pickup)
    if hours_late < 0:
        hours_late = 0.0

    threshold = contract.failed_pickup_hours if contract.failed_pickup_hours is not None else DEFAULT_HOURS
    if hours_late <= threshold:
        return CreditVerdict(
            False,
            None,
            False,
            ["BELOW_DELAY_THRESHOLD"],
            basis,
            round(hours_late, 2),
        )

    if contract.failed_pickup_amount is not None:
        amount = contract.failed_pickup_amount
        codes = ["CONTRACT_FIXED_CREDIT"]
    else:
        amount = min(DEFAULT_CAP, DEFAULT_PCT * order.shipment_fee_inr)
        codes = ["SOP_DEFAULT_CREDIT"]

    return CreditVerdict(
        True,
        amount,
        False,
        codes,
        basis,
        round(hours_late, 2),
        requires_manager_approval=amount > MANAGER_THRESHOLD,
        warnings=["Northstar monthly credit cap is INR 5000"] if contract.credit_monthly_cap else [],
    )
