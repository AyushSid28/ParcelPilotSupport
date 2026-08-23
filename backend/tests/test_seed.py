from app.clock import SNAPSHOT


def test_seed_counts(db):
    accounts = db.execute("SELECT account_id FROM accounts ORDER BY 1").fetchall()
    orders = db.execute("SELECT order_id FROM orders ORDER BY 1").fetchall()
    tickets = db.execute("SELECT ticket_id FROM tickets ORDER BY 1").fetchall()
    assert [r[0] for r in accounts] == ["ACCT-001", "ACCT-002", "ACCT-003", "ACCT-004"]
    assert [r[0] for r in orders] == [
        "ORD-1001",
        "ORD-1002",
        "ORD-2001",
        "ORD-2002",
        "ORD-3001",
        "ORD-4001",
    ]
    assert [r[0] for r in tickets] == [
        "TKT-450",
        "TKT-451",
        "TKT-501",
        "TKT-502",
        "TKT-503",
        "TKT-504",
        "TKT-505",
    ]


def test_snapshot_is_assessment_clock():
    assert SNAPSHOT.strftime("%Y-%m-%d %H:%M %Z") == "2026-08-16 11:00 IST"
