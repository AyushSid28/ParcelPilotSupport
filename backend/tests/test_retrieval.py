from app.auth import parse_actor
from app.retrieval.ingest import persist
from app.retrieval.search import search_documents


def test_deprecated_policy_is_not_current_authority(db):
    persist(db)
    staff = parse_actor("staff", None, "maya", "agent")
    hits = search_documents(db, staff, "Enterprise P1 first-response target")
    assert hits
    assert all(h["status"] != "deprecated" for h in hits)
    assert hits[0]["filename"] != "02_Support_Policy_v2_DEPRECATED.pdf"


def test_customer_cannot_retrieve_other_agreements(db):
    persist(db)
    customer = parse_actor("customer", "ACCT-001", None, None)
    hits = search_documents(db, customer, "cancellation fee booked shipment")
    files = {h["filename"] for h in hits}
    assert "06_LumenWorks_Service_Agreement.pdf" not in files
    assert "05_Northstar_Logistics_Enterprise_Agreement.pdf" in files


def test_staff_can_open_deprecated_when_asked(db):
    persist(db)
    staff = parse_actor("staff", None, "maya", "agent")
    hits = search_documents(db, staff, "DEPRECATED DO NOT USE", include_deprecated=True)
    assert any(h["status"] == "deprecated" for h in hits)
