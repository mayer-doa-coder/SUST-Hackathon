from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def load_samples() -> dict:
    sample_path = Path(__file__).resolve().parents[1] / "docs" / "SUST_Preli_Sample_Cases.json"
    return json.loads(sample_path.read_text(encoding="utf-8"))


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_ticket_returns_required_contract() -> None:
    payload = {
        "ticket_id": "TKT-REQ-001",
        "complaint": "I paid my electricity bill 850 taka but it deducted twice.",
        "language": "en",
        "channel": "in_app_chat",
        "user_type": "customer",
        "transaction_history": [
            {
                "transaction_id": "TXN-1",
                "timestamp": "2026-04-14T08:15:30Z",
                "type": "payment",
                "amount": 850,
                "counterparty": "BILLER-DESCO",
                "status": "completed",
            },
            {
                "transaction_id": "TXN-2",
                "timestamp": "2026-04-14T08:15:42Z",
                "type": "payment",
                "amount": 850,
                "counterparty": "BILLER-DESCO",
                "status": "completed",
            },
        ],
    }

    response = client.post("/analyze-ticket", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
        "ticket_id",
        "relevant_transaction_id",
        "evidence_verdict",
        "case_type",
        "severity",
        "department",
        "agent_summary",
        "recommended_next_action",
        "customer_reply",
        "human_review_required",
        "confidence",
        "reason_codes",
    }
    assert data["ticket_id"] == "TKT-REQ-001"
    assert data["evidence_verdict"] in {"consistent", "inconsistent", "insufficient_data"}
    assert data["case_type"] in {
        "wrong_transfer",
        "payment_failed",
        "refund_request",
        "duplicate_payment",
        "merchant_settlement_delay",
        "agent_cash_in_issue",
        "phishing_or_social_engineering",
        "other",
    }
    assert data["severity"] in {"low", "medium", "high", "critical"}
    assert data["department"] in {
        "customer_support",
        "dispute_resolution",
        "payments_ops",
        "merchant_operations",
        "agent_operations",
        "fraud_risk",
    }
    assert isinstance(data["agent_summary"], str)
    assert isinstance(data["recommended_next_action"], str)
    assert isinstance(data["customer_reply"], str)
    assert isinstance(data["human_review_required"], bool)


def test_extra_routes_are_not_exposed() -> None:
    assert client.get("/ready").status_code == 404
    assert client.post("/auth/login", json={}).status_code == 404
    assert client.get("/analysis/TKT-1").status_code == 404


def test_public_samples_meet_contract() -> None:
    samples = load_samples()
    for case in samples["cases"]:
        response = client.post("/analyze-ticket", json=case["input"])
        assert response.status_code == 200, case["id"]
        data = response.json()
        assert data["ticket_id"] == case["input"]["ticket_id"]
        assert "evidence_verdict" in data
        assert "case_type" in data
        assert "customer_reply" in data
        assert isinstance(data["human_review_required"], bool)
