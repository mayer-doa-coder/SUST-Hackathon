from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.evidence.repository import evidence_repository
from app.investigation.rules import rule_config_repository
from app.main import app
from app.messaging.repository import messaging_repository
from app.observability.registry import observability_registry
from app.tickets.repository import ticket_repository
from app.workflows.repository import workflow_repository


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_ticket_repository() -> None:
    ticket_repository.reset()
    evidence_repository.reset()
    rule_config_repository.reset()
    workflow_repository.reset()
    messaging_repository.reset()
    observability_registry.reset()


def load_samples() -> dict:
    sample_path = Path(__file__).resolve().parents[1] / "docs" / "SUST_Preli_Sample_Cases.json"
    return json.loads(sample_path.read_text(encoding="utf-8"))


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_gateway_adds_correlation_id() -> None:
    response = client.get("/health", headers={"X-Correlation-ID": "corr-test-1"})
    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == "corr-test-1"


def test_gateway_analysis_status_route_exists() -> None:
    response = client.get("/analysis/TKT-404")
    assert response.status_code == 200
    assert response.json()["case_id"] == "TKT-404"
    assert response.json()["status"] == "not_found"


def test_gateway_creates_ticket_intake_record_and_status() -> None:
    payload = {
        "ticket_id": "TKT-M3-1",
        "complaint": "I sent money but the receiver says they did not get it.",
        "transaction_history": [],
    }
    response = client.post("/analyze-ticket", json=payload, headers={"Idempotency-Key": "idem-m3-1"})
    assert response.status_code == 200
    assert response.json()["ticket_id"] == "TKT-M3-1"

    detail = client.get("/tickets/TKT-M3-1")
    assert detail.status_code == 200
    assert detail.json()["status"] == "completed"
    assert detail.json()["response"]["ticket_id"] == "TKT-M3-1"

    status = client.get("/analysis/TKT-M3-1")
    assert status.status_code == 200
    assert status.json()["status"] == "completed"


def test_ticket_intake_idempotency_reuses_existing_response() -> None:
    first_payload = {
        "ticket_id": "TKT-M3-IDEMPOTENT-1",
        "complaint": "Payment failed at merchant checkout.",
        "transaction_history": [],
    }
    second_payload = {
        "ticket_id": "TKT-M3-IDEMPOTENT-2",
        "complaint": "This different ticket should not replace the first one.",
        "transaction_history": [],
    }
    headers = {"Idempotency-Key": "same-idempotency-key"}

    first = client.post("/analyze-ticket", json=first_payload, headers=headers)
    second = client.post("/analyze-ticket", json=second_payload, headers=headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["ticket_id"] == first.json()["ticket_id"]

    missing_second = client.get("/tickets/TKT-M3-IDEMPOTENT-2")
    assert missing_second.status_code == 404
    assert missing_second.json()["error"]["code"] == "TICKET_NOT_FOUND"


def test_ticket_intake_records_outbox_events() -> None:
    payload = {
        "ticket_id": "TKT-M3-OUTBOX",
        "complaint": "I may have been tricked into sending money.",
        "transaction_history": [],
    }
    response = client.post("/tickets/analyze", json=payload, headers={"Idempotency-Key": "idem-outbox"})
    assert response.status_code == 200

    event_types = [event.event_type for event in ticket_repository.list_outbox()]
    assert "TicketAnalysisRequested" in event_types
    assert "TicketAnalysisCompleted" in event_types


def test_evidence_features_index_transactions_and_detect_duplicate_payment() -> None:
    payload = {
        "ticket_id": "TKT-EVIDENCE",
        "account_id": "ACC-1",
        "transactions": [
            {
                "transaction_id": "TXN-1",
                "timestamp": "2026-06-26T10:00:00+00:00",
                "type": "payment",
                "amount": 500,
                "counterparty": "MERCHANT-A",
                "status": "completed",
            },
            {
                "transaction_id": "TXN-2",
                "timestamp": "2026-06-26T10:00:30+00:00",
                "type": "payment",
                "amount": 500,
                "counterparty": "MERCHANT-A",
                "status": "completed",
            },
        ],
    }

    response = client.post("/evidence/features", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["account_id"] == "ACC-1"
    assert data["transaction_count"] == 2
    assert data["duplicate_payment"]["transaction_id"] == "TXN-2"
    assert isinstance(data["shard_id"], int)

    lookup = client.get("/transactions/TXN-2")
    assert lookup.status_code == 200
    assert lookup.json()["transaction"]["transaction_id"] == "TXN-2"

    account = client.get("/accounts/ACC-1/transactions")
    assert account.status_code == 200
    assert len(account.json()["transactions"]) == 2


def test_evidence_lookup_uses_cache_after_first_read() -> None:
    payload = {
        "ticket_id": "TKT-EVIDENCE-CACHE",
        "account_id": "ACC-CACHE",
        "transactions": [
            {
                "transaction_id": "TXN-CACHE",
                "timestamp": "2026-06-26T10:00:00+00:00",
                "type": "transfer",
                "amount": 1200,
                "counterparty": "+8801712345678",
                "status": "completed",
            }
        ],
    }
    assert client.post("/evidence/features", json=payload).status_code == 200

    first = client.get("/transactions/TXN-CACHE")
    second = client.get("/transactions/TXN-CACHE")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["cache_status"] == "miss"
    assert second.json()["cache_status"] == "hit"


def test_evidence_lookup_returns_controlled_not_found() -> None:
    response = client.get("/transactions/NO-SUCH-TXN")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TRANSACTION_NOT_FOUND"


def test_investigation_active_rules_endpoint_exposes_structured_ownership() -> None:
    response = client.get("/rules/active-version")
    assert response.status_code == 200
    data = response.json()
    assert data["rule_version"].startswith("rules-")
    assert data["owner"] == "investigation-service"
    assert "case_type" in data["structured_fields"]
    assert data["cache_status"] == "miss"

    cached = client.get("/rules/active-version")
    assert cached.status_code == 200
    assert cached.json()["cache_status"] == "hit"


def test_investigation_evaluate_returns_rule_owned_decision() -> None:
    payload = {
        "ticket_id": "TKT-M5-EVAL",
        "complaint": "I paid 500 taka twice at merchant checkout.",
        "transaction_history": [
            {
                "transaction_id": "TXN-M5-1",
                "timestamp": "2026-06-26T10:00:00+00:00",
                "type": "payment",
                "amount": 500,
                "counterparty": "MERCHANT-A",
                "status": "completed",
            },
            {
                "transaction_id": "TXN-M5-2",
                "timestamp": "2026-06-26T10:00:30+00:00",
                "type": "payment",
                "amount": 500,
                "counterparty": "MERCHANT-A",
                "status": "completed",
            },
        ],
    }
    response = client.post("/investigations/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["ticket_id"] == "TKT-M5-EVAL"
    assert data["case_type"] == "duplicate_payment"
    assert data["relevant_transaction_id"] == "TXN-M5-2"
    assert data["rule_version"].startswith("rules-")
    assert data["rules_cache_status"] in {"hit", "miss"}
    assert "agent_summary" not in data


def test_nlg_draft_uses_template_fallback_and_versions() -> None:
    payload = {
        "ticket_id": "TKT-M6-NLG",
        "complaint": "I paid 500 taka but merchant says payment failed.",
        "user_type": "customer",
        "decision": {
            "relevant_transaction_id": "TXN-M6-1",
            "evidence_verdict": "consistent",
            "case_type": "payment_failed",
            "severity": "high",
            "department": "payments_ops",
            "human_review_required": True,
            "confidence": 0.84,
            "reason_codes": ["transaction_match"],
            "language": "en",
        },
    }
    response = client.post("/nlg/draft", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["agent_summary"]
    assert data["recommended_next_action"]
    assert data["customer_reply"]
    assert data["used_fallback"] is True
    assert data["prompt_version"].startswith("nlg-prompt-")
    assert data["template_version"].startswith("nlg-template-")
    assert data["safety_policy_version"].startswith("safety-policy-")
    assert data["circuit_state"] == "closed"


def test_safety_validate_replaces_unsafe_reply() -> None:
    response = client.post(
        "/safety/validate",
        json={
            "ticket_id": "TKT-M6-SAFE",
            "customer_reply": "We will refund you now. Share your OTP to continue.",
            "language": "en",
            "user_type": "customer",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["safe"] is False
    assert data["replaced"] is True
    assert "We will refund" not in data["customer_reply"]
    assert data["safety_policy_version"].startswith("safety-policy-")


def test_analysis_response_contains_nlg_and_safety_versions() -> None:
    payload = {
        "ticket_id": "TKT-M6-ANALYSIS",
        "complaint": "I paid 500 taka but merchant says payment failed.",
        "transaction_history": [
            {
                "transaction_id": "TXN-M6-ANALYSIS",
                "timestamp": "2026-06-26T10:00:00+00:00",
                "type": "payment",
                "amount": 500,
                "counterparty": "MERCHANT-A",
                "status": "failed",
            }
        ],
    }
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    reason_codes = response.json()["reason_codes"]
    assert any(code.startswith("nlg_template_") for code in reason_codes)
    assert any(code.startswith("safety_policy_") for code in reason_codes)


def test_workflow_start_step_idempotency_and_compensation() -> None:
    start_payload = {
        "case_id": "WF-1",
        "ticket_id": "WF-1",
        "idempotency_key": "wf-idem-1",
        "correlation_id": "corr-wf-1",
    }
    start = client.post("/workflows/analyze-ticket/start", json=start_payload)
    replay_start = client.post("/workflows/analyze-ticket/start", json=start_payload)
    assert start.status_code == 200
    assert replay_start.status_code == 200
    assert start.json()["case_id"] == replay_start.json()["case_id"]
    assert start.json()["current_step"] == "evidence"

    step_payload = {"event_id": "event-evidence-1", "payload": {"transaction_count": 2}}
    step = client.post("/workflows/WF-1/steps/evidence-complete", json=step_payload)
    replay_step = client.post("/workflows/WF-1/steps/evidence-complete", json=step_payload)
    assert step.status_code == 200
    assert step.json()["status"] == "in_progress"
    assert replay_step.status_code == 200
    assert replay_step.json()["idempotent_replay"] is True

    compensate = client.post("/workflows/WF-1/compensate", json={"reason": "manual rollback", "event_id": "comp-1"})
    assert compensate.status_code == 200
    assert compensate.json()["status"] == "compensated"
    assert compensate.json()["compensation_reason"] == "manual rollback"


def test_workflow_failure_can_retry() -> None:
    client.post(
        "/workflows/analyze-ticket/start",
        json={"case_id": "WF-RETRY", "ticket_id": "WF-RETRY", "idempotency_key": "wf-retry", "correlation_id": "corr"},
    )
    failed = client.post(
        "/workflows/WF-RETRY/steps/evidence-complete",
        json={"event_id": "event-fail-1", "status": "failed", "payload": {"error": "timeout"}},
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"

    retry = client.post("/workflows/WF-RETRY/retry")
    assert retry.status_code == 200
    assert retry.json()["status"] == "in_progress"
    assert retry.json()["retry_count"] == 1
    assert retry.json()["current_step"] == "evidence"


def test_ticket_intake_completes_workflow_saga() -> None:
    payload = {
        "ticket_id": "TKT-M7-SAGA",
        "complaint": "Payment failed at merchant checkout.",
        "transaction_history": [],
    }
    response = client.post("/analyze-ticket", json=payload, headers={"Idempotency-Key": "idem-m7"})
    assert response.status_code == 200

    workflow = client.get("/workflows/TKT-M7-SAGA")
    assert workflow.status_code == 200
    data = workflow.json()
    assert data["status"] == "completed"
    assert data["completed_steps"] == ["evidence", "investigation", "nlg"]
    assert data["current_step"] is None


def test_pubsub_publish_is_replay_safe_and_audited() -> None:
    payload = {
        "event_id": "event-pubsub-1",
        "event_type": "TicketAnalysisRequested",
        "case_id": "CASE-PUBSUB",
        "correlation_id": "corr-pubsub",
        "payload": {"ticket_id": "CASE-PUBSUB"},
    }
    first = client.post("/events/publish", json=payload)
    replay = client.post("/events/publish", json=payload)
    assert first.status_code == 200
    assert first.json()["published"] is True
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True

    audit = client.get("/audit/events/CASE-PUBSUB")
    assert audit.status_code == 200
    assert len(audit.json()["events"]) == 1
    assert audit.json()["events"][0]["event_id"] == "event-pubsub-1"


def test_pubsub_routes_completed_cases_to_department_queue() -> None:
    payload = {
        "event_id": "event-route-1",
        "event_type": "TicketAnalysisCompleted",
        "case_id": "CASE-ROUTE",
        "correlation_id": "corr-route",
        "payload": {
            "ticket_id": "CASE-ROUTE",
            "department": "fraud_risk",
            "severity": "critical",
            "case_type": "phishing_or_social_engineering",
        },
    }
    response = client.post("/events/publish", json=payload)
    assert response.status_code == 200
    routed = client.get("/routing/departments/fraud_risk/cases")
    assert routed.status_code == 200
    cases = routed.json()["cases"]
    assert len(cases) == 1
    assert cases[0]["case_id"] == "CASE-ROUTE"
    assert cases[0]["priority"] == "high"


def test_pubsub_dead_letter_records_failed_events() -> None:
    response = client.post(
        "/events/publish",
        json={
            "event_id": "event-dlq-1",
            "event_type": "TicketAnalysisCompleted",
            "case_id": "CASE-DLQ",
            "correlation_id": "corr-dlq",
            "payload": {"force_dead_letter": True},
        },
    )
    assert response.status_code == 200
    assert response.json()["dead_lettered"] is True

    dead_letters = client.get("/events/dead-letter")
    assert dead_letters.status_code == 200
    assert dead_letters.json()["events"][0]["event_id"] == "event-dlq-1"


def test_ticket_intake_publishes_audit_and_department_route() -> None:
    payload = {
        "ticket_id": "TKT-M8-ROUTE",
        "complaint": "Someone called me and asked for my OTP.",
        "transaction_history": [],
    }
    response = client.post("/analyze-ticket", json=payload, headers={"Idempotency-Key": "idem-m8"})
    assert response.status_code == 200
    assert response.json()["department"] == "fraud_risk"

    audit = client.get("/audit/events/TKT-M8-ROUTE")
    assert audit.status_code == 200
    event_types = [event["event_type"] for event in audit.json()["events"]]
    assert "TicketAnalysisRequested" in event_types
    assert "TicketAnalysisCompleted" in event_types

    routed = client.get("/routing/departments/fraud_risk/cases")
    assert routed.status_code == 200
    assert routed.json()["cases"][0]["case_id"] == "TKT-M8-ROUTE"


def test_platform_scaling_plan_exposes_replicas_db_cache_and_load_test() -> None:
    response = client.get("/platform/scaling-plan")
    assert response.status_code == 200
    data = response.json()
    services = {item["service"]: item for item in data["service_replicas"]}
    assert services["api-gateway"]["replicas"] >= 1
    assert services["transaction-evidence"]["load_balancer_scope"] == "internal"
    assert data["database_scaling"][0]["write_target"].startswith("postgresql://")
    assert data["database_scaling"][0]["read_targets"]
    assert data["shard_routing"]["shard_key"] == "account_id"
    assert data["cache_policy"]["ttl_seconds"]["transactions"] > 0
    assert data["load_test_plan"]["target_endpoint"] == "POST /analyze-ticket"


def test_platform_database_route_separates_reads_and_writes() -> None:
    read = client.get("/platform/database-route", params={"operation": "read"})
    write = client.get("/platform/database-route", params={"operation": "write"})
    read_your_write = client.get("/platform/database-route", params={"operation": "read", "read_your_write": "true"})

    assert read.status_code == 200
    assert write.status_code == 200
    assert read_your_write.status_code == 200
    assert read.json()["consistency"] == "eventual read replica"
    assert write.json()["consistency"] == "strong primary read/write"
    assert read_your_write.json()["consistency"] == "strong primary read/write"
    assert read.json()["target"] != write.json()["target"]


def test_platform_transaction_shard_route_is_deterministic() -> None:
    first = client.get("/platform/transaction-shards/ACC-9001")
    second = client.get("/platform/transaction-shards/ACC-9001")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["shard_id"] == second.json()["shard_id"]
    assert first.json()["shard_count"] >= 1
    assert first.json()["strategy"] == get_settings().transaction_shard_strategy


def test_observability_ready_metrics_and_traces() -> None:
    health = client.get("/health", headers={"X-Correlation-ID": "corr-obs-1"})
    ready = client.get("/ready")
    metrics = client.get("/metrics")
    traces = client.get("/observability/traces")

    assert health.status_code == 200
    assert "X-Response-Time-ms" in health.headers
    assert ready.status_code == 200
    assert ready.json()["status"] == "ok"
    assert any(component["name"] == "api-gateway" for component in ready.json()["components"])
    assert metrics.status_code == 200
    assert "queuestorm_http_requests_total" in metrics.text
    assert traces.status_code == 200
    assert any(trace["correlation_id"] == "corr-obs-1" for trace in traces.json()["traces"])


def test_deployment_scaffolding_files_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    expected_files = [
        "docker-compose.yml",
        ".dockerignore",
        "deploy/k8s/namespace.yaml",
        "deploy/k8s/configmap.yaml",
        "deploy/k8s/deployment.yaml",
        "deploy/k8s/service.yaml",
        "deploy/k8s/hpa.yaml",
        "docs/RUNBOOK.md",
    ]
    for relative_path in expected_files:
        assert (root / relative_path).exists(), relative_path


def test_auth_login_refresh_jwks_and_logout() -> None:
    settings = get_settings()
    response = client.post(
        "/auth/login",
        json={"username": settings.auth_demo_username, "password": settings.auth_demo_password},
    )
    assert response.status_code == 200
    tokens = response.json()
    assert tokens["token_type"] == "Bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert "support_agent" in tokens["roles"]

    refresh_response = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh_response.status_code == 200
    assert refresh_response.json()["access_token"]

    jwks_response = client.get("/auth/jwks")
    assert jwks_response.status_code == 200
    assert jwks_response.json()["keys"][0]["kid"] == "default-hs256"

    logout_response = client.post("/auth/logout", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert logout_response.status_code == 200
    assert logout_response.json()["status"] == "ok"

    revoked_response = client.post(
        "/auth/logout",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert revoked_response.status_code == 401
    assert revoked_response.json()["error"]["code"] == "TOKEN_REVOKED"


def test_gateway_rejects_missing_token_when_auth_required() -> None:
    settings = get_settings()
    original = settings.auth_required
    settings.auth_required = True
    try:
        response = client.get("/analysis/TKT-AUTH")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTH_REQUIRED"
    finally:
        settings.auth_required = original


def test_gateway_accepts_valid_token_when_auth_required() -> None:
    settings = get_settings()
    login = client.post(
        "/auth/login",
        json={"username": settings.auth_demo_username, "password": settings.auth_demo_password},
    )
    token = login.json()["access_token"]

    original = settings.auth_required
    settings.auth_required = True
    try:
        response = client.get("/analysis/TKT-AUTH", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["case_id"] == "TKT-AUTH"
    finally:
        settings.auth_required = original


def test_gateway_rate_limit_can_reject_bursts() -> None:
    settings = get_settings()
    original_enabled = settings.rate_limit_enabled
    original_requests = settings.rate_limit_requests
    original_window = settings.rate_limit_window_seconds
    settings.rate_limit_enabled = True
    settings.rate_limit_requests = 1
    settings.rate_limit_window_seconds = 60
    try:
        headers = {"Authorization": "Bearer rate-limit-test-token"}
        first = client.get("/analysis/TKT-RATE", headers=headers)
        second = client.get("/analysis/TKT-RATE", headers=headers)
        assert first.status_code == 200
        assert second.status_code == 429
        assert second.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    finally:
        settings.rate_limit_enabled = original_enabled
        settings.rate_limit_requests = original_requests
        settings.rate_limit_window_seconds = original_window


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

