from app.auth import NotFound, parse_actor
from app.store import Store


def test_customer_cannot_see_foreign_order(db):
    store = Store(db)
    northstar = parse_actor("customer", "ACCT-001", None, None)
    try:
        store.order(northstar, "ORD-2001")
        assert False, "should not see LumenWorks order"
    except NotFound:
        pass
    own = store.order(northstar, "ORD-1001")
    assert own.order_id == "ORD-1001"


def test_missing_and_forbidden_look_the_same(db):
    store = Store(db)
    northstar = parse_actor("customer", "ACCT-001", None, None)
    try:
        store.order(northstar, "ORD-2001")
    except NotFound as hidden:
        hidden_type = type(hidden)
    try:
        store.order(northstar, "ORD-NOPE")
    except NotFound as missing:
        assert type(missing) is hidden_type


def test_staff_sees_all_accounts(db):
    store = Store(db)
    staff = parse_actor("staff", None, "maya", "agent")
    ids = {a.account_id for a in store.accounts(staff)}
    assert ids == {"ACCT-001", "ACCT-002", "ACCT-003", "ACCT-004"}
    assert store.order(staff, "ORD-2001").account_id == "ACCT-002"


def test_customer_list_is_scoped(db):
    store = Store(db)
    customer = parse_actor("customer", "ACCT-002", None, None)
    assert {o.order_id for o in store.orders(customer)} == {"ORD-2001", "ORD-2002"}
    assert {t.ticket_id for t in store.tickets(customer)} == {"TKT-451", "TKT-502"}


def test_customer_requires_account_header():
    try:
        parse_actor("customer", None, None, None)
        assert False
    except ValueError:
        pass
