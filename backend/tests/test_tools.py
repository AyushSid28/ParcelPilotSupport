from app.auth import parse_actor
from app.tools import run
from app import actions as action_store
from app.pulse import detect
from app.store import Store
from app.retrieval.ingest import persist


def test_tools_respect_acl(db):
    persist(db)
    customer = parse_actor("customer", "ACCT-001", None, None)
    hidden = run("get_order", {"order_id": "ORD-2001"}, customer, db)
    assert hidden == {"error": "not_found", "scope": "this_account"}
    own = run("get_order", {"order_id": "ORD-1001"}, customer, db)
    assert own["order_id"] == "ORD-1001"


def test_cancellation_tool_uses_contract(db):
    persist(db)
    customer = parse_actor("customer", "ACCT-001", None, None)
    verdict = run("assess_cancellation", {"order_id": "ORD-1001"}, customer, db)
    assert verdict["fee_inr"] == 0
    assert any(c["ignored"] == "TKT-450" for c in verdict["conflicts"])


def test_credit_tool(db):
    staff = parse_actor("staff", None, "maya", "agent")
    verdict = run("assess_failed_pickup_credit", {"order_id": "ORD-2002"}, staff, db)
    assert verdict["amount_inr"] == 300


def test_propose_does_not_write_escalation(db):
    staff = parse_actor("staff", None, "maya", "agent")
    preview = run("propose_escalation", {"ticket_id": "TKT-505", "reason": "P1 breach", "priority": "P1"}, staff, db)
    assert preview["needs_confirmation"] is True
    assert db.execute("SELECT COUNT(*) FROM escalations").fetchone()[0] == 0
    done = action_store.confirm(db, staff, preview["proposal_id"])
    assert db.execute("SELECT COUNT(*) FROM escalations").fetchone()[0] == 1
    again = action_store.confirm(db, staff, preview["proposal_id"])
    assert again["idempotent"] is True
    assert db.execute("SELECT COUNT(*) FROM escalations").fetchone()[0] == 1


def test_customer_cannot_confirm_other_account_proposal(db):
    staff = parse_actor("staff", None, "maya", "agent")
    preview = run("propose_escalation", {"ticket_id": "TKT-505", "reason": "key", "priority": "P1"}, staff, db)
    stranger = parse_actor("customer", "ACCT-001", None, None)
    try:
        action_store.confirm(db, stranger, preview["proposal_id"])
        assert False
    except Exception:
        pass
    assert db.execute("SELECT COUNT(*) FROM escalations").fetchone()[0] == 0


def test_pulse_flags_breaches(db):
    persist(db)
    staff = parse_actor("staff", None, "priya", "ops_lead")
    issues = detect(Store(db), staff)
    ids = {i["id"] for i in issues}
    assert "sla-TKT-501" in ids
    assert "sla-TKT-505" in ids
    assert "cluster-bulk-csv" in ids
    assert "pickup-ORD-2002" in ids


def test_customer_pulse_hidden(db):
    customer = parse_actor("customer", "ACCT-001", None, None)
    out = run("get_ops_pulse", {}, customer, db)
    assert out == {"error": "not_found"}
