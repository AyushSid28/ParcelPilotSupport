from app.clock import now
from app.mapping import account_from_row, order_from_row, ticket_from_row
from app.models import Order
from app.policy.cancellation import assess_cancellation
from app.policy.credits import assess_failed_pickup_credit
from app.policy.sla import assess_sla


def _acc(db, account_id):
    return account_from_row(db.execute("SELECT * FROM accounts WHERE account_id=?", (account_id,)).fetchone())


def _ord(db, order_id):
    return order_from_row(db.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone())


def _tix(db, ticket_id):
    return ticket_from_row(db.execute("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)).fetchone())


def test_northstar_booked_cancel_is_free(db):
    order, account = _ord(db, "ORD-1001"), _acc(db, "ACCT-001")
    history = [_tix(db, "TKT-450")]
    verdict = assess_cancellation(order, account, now(), history)
    assert verdict.allowed is True
    assert verdict.fee_inr == 0
    assert "CONTRACT_WAIVES_FEE" in verdict.reason_codes
    assert any(c["ignored"] == "TKT-450" for c in verdict.conflicts)


def test_northstar_picked_up_cannot_cancel(db):
    verdict = assess_cancellation(_ord(db, "ORD-1002"), _acc(db, "ACCT-001"), now())
    assert verdict.allowed is False
    assert verdict.next_step == "return_to_origin"


def test_lumenworks_cancel_after_window_is_charged(db):
    verdict = assess_cancellation(_ord(db, "ORD-2001"), _acc(db, "ACCT-002"), now())
    assert verdict.allowed is True
    assert verdict.fee_inr == 250


def test_beacon_within_free_window(db):
    verdict = assess_cancellation(_ord(db, "ORD-3001"), _acc(db, "ACCT-003"), now())
    assert verdict.allowed is True
    assert verdict.fee_inr == 0
    assert "WITHIN_FREE_WINDOW" in verdict.reason_codes


def test_delivered_cannot_cancel(db):
    verdict = assess_cancellation(_ord(db, "ORD-4001"), _acc(db, "ACCT-004"), now())
    assert verdict.allowed is False


def test_lumenworks_late_pickup_fixed_credit(db):
    verdict = assess_failed_pickup_credit(_ord(db, "ORD-2002"), _acc(db, "ACCT-002"), now())
    assert verdict.eligible is True
    assert verdict.amount_inr == 300
    assert verdict.hours_late == 4.5
    assert "CONTRACT_FIXED_CREDIT" in verdict.reason_codes


def test_default_credit_uses_sop_formula(db):
    base = _ord(db, "ORD-2002")
    order = Order(**{**base.__dict__, "account_id": "ACCT-003"})
    verdict = assess_failed_pickup_credit(order, _acc(db, "ACCT-003"), now())
    assert verdict.eligible is True
    assert verdict.amount_inr == 240  # min(500, 10% of 2400)


def test_credit_refuses_unknown_fault(db):
    base = _ord(db, "ORD-2002")
    order = Order(**{**base.__dict__, "carrier_fault": None})
    verdict = assess_failed_pickup_credit(order, _acc(db, "ACCT-002"), now())
    assert verdict.uncertain is True
    assert verdict.eligible is False


def test_p1_outage_breaches_northstar_sla(db):
    verdict = assess_sla(_tix(db, "TKT-501"), _acc(db, "ACCT-001"), now())
    assert verdict.severity == "P1"
    assert verdict.target_minutes == 15
    assert verdict.breached is True


def test_api_key_exposure_breaches_enterprise_sla(db):
    verdict = assess_sla(_tix(db, "TKT-505"), _acc(db, "ACCT-004"), now())
    assert verdict.severity == "P1"
    assert verdict.target_minutes == 30
    assert verdict.breached is True
    assert "01_Support_Policy_v3_CURRENT.pdf" in verdict.policy_basis


def test_lumenworks_bulk_upload_is_p2_not_breached_on_sunday(db):
    verdict = assess_sla(_tix(db, "TKT-502"), _acc(db, "ACCT-002"), now())
    assert verdict.severity == "P2"
    assert verdict.clock == "business"
    assert verdict.breached is False


def test_billing_contact_is_p3(db):
    verdict = assess_sla(_tix(db, "TKT-503"), _acc(db, "ACCT-003"), now())
    assert verdict.severity == "P3"


def test_draft_cancels_free(db):
    base = _ord(db, "ORD-3001")
    order = Order(**{**base.__dict__, "status": "DRAFT"})
    verdict = assess_cancellation(order, _acc(db, "ACCT-003"), now())
    assert verdict.allowed is True
    assert verdict.fee_inr == 0


def test_customer_fault_blocks_credit(db):
    base = _ord(db, "ORD-2002")
    order = Order(**{**base.__dict__, "customer_fault": True})
    verdict = assess_failed_pickup_credit(order, _acc(db, "ACCT-002"), now())
    assert verdict.eligible is False
    assert "CUSTOMER_FAULT" in verdict.reason_codes
