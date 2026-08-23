from fastapi.testclient import TestClient

from app.main import app


def test_health_and_pulse():
    with TestClient(app) as client:
        health = client.get("/health").json()
        assert health["ok"] is True
        assert health["accounts"] == 4
        assert health["tickets"] == 7

        pulse = client.get(
            "/ops/pulse",
            headers={"X-Actor-Type": "staff", "X-Staff-Id": "ops", "X-Staff-Role": "ops_lead"},
        ).json()
        ids = {i["id"] for i in pulse["issues"]}
        assert "sla-TKT-505" in ids

        hidden = client.get(
            "/orders",
            headers={"X-Actor-Type": "customer", "X-Account-Id": "ACCT-001"},
        ).json()
        assert {o["order_id"] for o in hidden["orders"]} == {"ORD-1001", "ORD-1002"}
        assert hidden["orders"][0]["account_name"] == "Northstar Logistics"
