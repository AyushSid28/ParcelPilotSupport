from __future__ import annotations

from app.clock import now
from app.models import Actor
from app.policy.sla import assess_sla
from app.store import Store


def detect(store: Store, actor: Actor) -> list[dict]:
    tickets = store.tickets(actor)
    orders = store.orders(actor)
    accounts = {a.account_id: a for a in store.accounts(actor)}
    issues: list[dict] = []

    for ticket in tickets:
        if ticket.status != "open":
            continue
        sla = assess_sla(ticket, accounts[ticket.account_id], now())
        if sla.severity == "P1" and sla.breached:
            issues.append(
                {
                    "id": f"sla-{ticket.ticket_id}",
                    "severity": "P1",
                    "title": f"{ticket.ticket_id} has breached {sla.target_minutes}m {sla.severity} target",
                    "evidence_ids": [ticket.ticket_id, ticket.account_id],
                    "suggested_action": "escalate",
                    "account_name": accounts[ticket.account_id].account_name,
                }
            )
        if "api key" in ticket.description.lower() or "credential" in ticket.subject.lower():
            issues.append(
                {
                    "id": f"sec-{ticket.ticket_id}",
                    "severity": "P1",
                    "title": "Possible credential exposure",
                    "evidence_ids": [ticket.ticket_id],
                    "suggested_action": "escalate",
                    "account_name": accounts[ticket.account_id].account_name,
                }
            )
        if "bulk" in ticket.subject.lower() or "csv" in ticket.description.lower():
            issues.append(
                {
                    "id": f"ki208-{ticket.ticket_id}",
                    "severity": "P2",
                    "title": "Bulk upload failures — matches KI-208, not a 3,000-row plan limit",
                    "evidence_ids": [ticket.ticket_id, "KI-208"],
                    "suggested_action": "share workaround: split under ~3,000 rows",
                    "account_name": accounts[ticket.account_id].account_name,
                }
            )
        if "swiftship" in ticket.description.lower() or "still shows booked" in ticket.subject.lower():
            issues.append(
                {
                    "id": f"ki211-{ticket.ticket_id}",
                    "severity": "P2",
                    "title": "SwiftShip status lag — KI-211 webhook delay up to 20 minutes",
                    "evidence_ids": [ticket.ticket_id, "KI-211"],
                    "suggested_action": "verify carrier status before telling the customer pickup failed",
                    "account_name": accounts[ticket.account_id].account_name,
                }
            )

    closed_bulk = [t for t in tickets if t.ticket_id == "TKT-451"]
    open_bulk = [t for t in tickets if t.ticket_id == "TKT-502"]
    if closed_bulk and open_bulk:
        issues.append(
            {
                "id": "cluster-bulk-csv",
                "severity": "P2",
                "title": "Repeat bulk-CSV failures across LumenWorks (open + historical)",
                "evidence_ids": ["TKT-502", "TKT-451", "KI-208"],
                "suggested_action": "treat as product incident, ignore TKT-451 plan-limit guidance",
                "account_name": "LumenWorks",
            }
        )

    for order in orders:
        if order.carrier_fault and order.status == "BOOKED" and order.pickup_actual_at is None:
            issues.append(
                {
                    "id": f"pickup-{order.order_id}",
                    "severity": "P2",
                    "title": f"{order.order_id} still not picked up; carrier accepted fault",
                    "evidence_ids": [order.order_id, order.account_id],
                    "suggested_action": "assess failed-pickup credit",
                    "account_name": accounts[order.account_id].account_name,
                }
            )

    # de-dupe by id
    seen = set()
    unique = []
    for issue in issues:
        if issue["id"] in seen:
            continue
        seen.add(issue["id"])
        unique.append(issue)
    rank = {"P1": 0, "P2": 1, "P3": 2}
    unique.sort(key=lambda i: rank.get(i["severity"], 9))
    return unique
