from dataclasses import dataclass

from app.models import Account, Ticket
from app.policy.contracts import SlaTarget, for_account
from app.policy.timeutil import business_minutes, minutes_between

POLICY_V3 = "01_Support_Policy_v3_CURRENT.pdf"


@dataclass
class SlaVerdict:
    severity: str
    target_minutes: int
    clock: str
    elapsed_minutes: float
    breached: bool
    policy_basis: list[str]
    reason_codes: list[str]

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "target_minutes": self.target_minutes,
            "clock": self.clock,
            "elapsed_minutes": round(self.elapsed_minutes, 1),
            "breached": self.breached,
            "policy_basis": self.policy_basis,
            "reason_codes": self.reason_codes,
        }


def classify_severity(ticket: Ticket) -> tuple[str, list[str]]:
    blob = f"{ticket.subject} {ticket.description}".lower()
    if any(w in blob for w in ("api key", "credential", "security incident", "exposure")):
        return "P1", ["SECURITY_OR_CREDENTIAL"]
    if "all shipment" in blob or ("http 500" in blob and "creating" in blob):
        return "P1", ["PRODUCTION_CREATE_OUTAGE"]
    if "bulk upload" in blob or "csv" in blob:
        return "P2", ["MAJOR_FEATURE_WITH_WORKAROUND"]
    if "booked" in blob and "pickup" in blob:
        return "P2", ["STATUS_DEGRADED_KNOWN_ISSUE"]
    if any(w in blob for w in ("how do", "billing contact", "how-to")):
        return "P3", ["HOW_TO"]
    return "P3", ["LIMITED_IMPACT"]


def assess_sla(ticket: Ticket, account: Account, now) -> SlaVerdict:
    severity, codes = classify_severity(ticket)
    contract = for_account(account)
    target: SlaTarget = {"P1": contract.p1, "P2": contract.p2, "P3": contract.p3}[severity]
    basis = [POLICY_V3]
    if contract.agreement_file:
        basis.insert(0, contract.agreement_file)

    if target.around_the_clock or target.clock == "wall":
        elapsed = minutes_between(ticket.created_at, now)
    else:
        elapsed = business_minutes(ticket.created_at, now)

    return SlaVerdict(
        severity=severity,
        target_minutes=target.minutes,
        clock="wall" if target.around_the_clock or target.clock == "wall" else "business",
        elapsed_minutes=elapsed,
        breached=elapsed > target.minutes,
        policy_basis=basis,
        reason_codes=codes,
    )
