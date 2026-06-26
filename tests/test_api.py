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


def test_missing_required_field_returns_400() -> None:
    response = client.post("/analyze-ticket", json={"ticket_id": "TKT-ERR"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MISSING_REQUIRED_FIELD"


def test_empty_complaint_returns_422() -> None:
    response = client.post("/analyze-ticket", json={"ticket_id": "TKT-ERR", "complaint": "   "})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_COMPLAINT"


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

