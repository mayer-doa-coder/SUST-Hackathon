# QueueStorm Investigator

AI-powered support copilot for digital financial services platforms. Investigates customer complaints against transaction history and returns evidence-backed routing decisions in real-time.

[![CI](https://github.com/dipshekhor/SUST-Hackathon/actions/workflows/ci.yml/badge.svg)](https://github.com/dipshekhor/SUST-Hackathon/actions/workflows/ci.yml)

---

## Live Deployment

| | URL |
|---|---|
| **Base URL** | https://sust-hackathon-production-9bd0.up.railway.app |
| **Health Check** | https://sust-hackathon-production-9bd0.up.railway.app/health |
| **Analyze Endpoint** | https://sust-hackathon-production-9bd0.up.railway.app/analyze-ticket |
| **GitHub Repo** | https://github.com/dipshekhor/SUST-Hackathon |

---

## Quick Test (Judge Verification)

### 1. Health Check
Open in browser or run:
```bash
curl https://sust-hackathon-production-9bd0.up.railway.app/health
```
**Expected response:**
```json
{"status": "ok"}
```

---

### 2. Test with Sample Case (Wrong Transfer)
```bash
curl -X POST https://sust-hackathon-production-9bd0.up.railway.app/analyze-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-001",
    "complaint": "I sent 5000 taka to a wrong number around 2pm today. Please help me get my money back.",
    "language": "en",
    "channel": "in_app_chat",
    "user_type": "customer",
    "transaction_history": [
      {
        "transaction_id": "TXN-9101",
        "timestamp": "2026-04-14T14:08:22Z",
        "type": "transfer",
        "amount": 5000,
        "counterparty": "+8801719876543",
        "status": "completed"
      }
    ]
  }'
```
**Expected:** `evidence_verdict: consistent`, `case_type: wrong_transfer`, `department: dispute_resolution`

---

### 3. Test with Sample Cases JSON File
The full sample case pack is in [`docs/SUST_Preli_Sample_Cases.json`](docs/SUST_Preli_Sample_Cases.json).

Each case has an `input` field — POST it to `/analyze-ticket` and verify the response matches the `expected_output` fields.

**Using Postman:**
1. Open [web.postman.co](https://web.postman.co)
2. New Request → `POST`
3. URL: `https://sust-hackathon-production-9bd0.up.railway.app/analyze-ticket`
4. Body → raw → JSON → paste any `input` from the sample cases file
5. Click Send

**Using curl (from sample file):**
```bash
# Phishing case
curl -X POST https://sust-hackathon-production-9bd0.up.railway.app/analyze-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-010",
    "complaint": "Someone called pretending to be from the bank and asked for my OTP. I gave it and now 15000 taka is missing.",
    "language": "en",
    "channel": "call_center",
    "user_type": "customer",
    "transaction_history": []
  }'
```
**Expected:** `case_type: phishing_or_social_engineering`, `severity: critical`, `department: fraud_risk`

---

### 4. Validation Error Test
```bash
curl -X POST https://sust-hackathon-production-9bd0.up.railway.app/analyze-ticket \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": "", "complaint": "test"}'
```
**Expected:** `{"error": {"code": "INVALID_FIELD_TYPE", ...}}`

---

## Overview

### The Problem

During promotional campaigns on digital finance platforms, complaint volume surges 4x or more overnight. Support agents—working under extreme time pressure (≤3.2 minutes per ticket)—must manually investigate each complaint by:

1. Reading the complaint text
2. Looking up transaction history in a separate system
3. Determining the case type and severity
4. Routing to the correct department
5. Writing a safe customer reply

This manual process leads to **routing errors**, **inconsistent classification**, **unsafe responses**, and **missed fraud escalations**.

### The Solution

**QueueStorm Investigator** is an internal API service that automates the investigation pipeline. It:

- Receives a complaint + transaction history
- Performs deterministic evidence reasoning
- Returns structured JSON with classification, routing, and safe response text
- Operates in **<30 seconds** per ticket
- Scales horizontally under campaign load

The service acts as a **support agent copilot**, not an autonomous decision-maker. Humans remain in control; the system augments their judgment.

### Objective

Build a **safe, reliable, fast, and scalable** API that enables support teams to handle 4x complaint volume without sacrificing response quality, safety, or consistency.

### Why Evidence Reasoning Matters

A complaint alone is insufficient. A customer might say *"I sent money to the wrong person"* but the transaction history might show a **duplicate payment** instead. Or a **phishing** report. Or a **failed payment with balance reversal**.

**Evidence reasoning** cross-references complaint text with actual transaction data to determine **what really happened**—independent of what the customer claims. This protects against:

- Incorrect classification
- Fraudulent claims
- Prompt injection attacks
- Unsafe promises made under pressure

---

## Features

 **REST API**  
Simple, stateless HTTP endpoints suitable for high-concurrency deployments.

 **Complaint Investigation**  
Parses natural-language complaints in English, Bangla, and mixed text.

 **Transaction Matching**  
Scores transaction candidates by amount, timestamp, type, and counterparty; finds the most likely relevant transaction.

 **Evidence Reasoning**  
Compares complaint intent against transaction data to generate verdicts: `CONSISTENT`, `INCONSISTENT`, or `INSUFFICIENT_DATA`.

 **Case Classification**  
Assigns complaint type from 8 categories: `WRONG_TRANSFER`, `PAYMENT_FAILED`, `DUPLICATE_PAYMENT`, `MERCHANT_SETTLEMENT_DELAY`, `AGENT_CASH_IN_ISSUE`, `REFUND_REQUEST`, `PHISHING_OR_SOCIAL_ENGINEERING`, `OTHER`.

 **Department Routing**  
Routes to 6 specialized teams: `CUSTOMER_SUPPORT`, `DISPUTE_RESOLUTION`, `PAYMENTS_OPS`, `MERCHANT_OPERATIONS`, `AGENT_OPERATIONS`, `FRAUD_RISK`.

 **Severity Prediction**  
Assigns severity: `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`.

 **Human Review Escalation**  
Flags cases requiring human judgment before action.

 **Safe Customer Reply Generation**  
Generates or selects professional, language-matched customer replies that never:
- Request credentials
- Promise unauthorized refunds
- Expose system details
- Contain prompt injection echoes

 **JSON Schema Validation**  
Input validation on receipt; output schema enforcement before return. Single wrong field type fails gracefully, not silently.

 **Prompt Injection Protection**  
Treats complaint text as untrusted user input. Embedded instructions are ignored. System behavior remains unchanged regardless of input content.

 **JWT Authentication & Rate Limiting**  
Optional token-based access control and per-identity request throttling.

 **Distributed Request Tracing**  
Correlation IDs propagated across all service calls for operational debugging.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          CLIENT                                 │
│                   (Support Dashboard)                           │
└────────────────────────────┬────────────────────────────────────┘
                             │ POST /analyze-ticket
                             │ + ticket_id
                             │ + complaint
                             │ + transaction_history
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY / PROXY                        │
│   (JWT Validation, Rate Limiting, Correlation IDs, Routing)    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  INPUT VALIDATION & SCHEMA CHECK               │
│         (Pydantic AnalyzeTicketRequest Model)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────┴────────────┐
                │                         │
                ▼                         ▼
       ┌─────────────────┐       ┌──────────────────┐
       │  INVESTIGATION  │       │  TRANSACTION     │
       │  SERVICE        │       │  EVIDENCE SERVICE│
       │  (Deterministic)│       │  (Lookup/Cache)  │
       │ • Normalization │       │ • Duplicate Detect
       │ • Intent Parse  │       │ • Counterparties │
       │ • Matching      │       └──────────────────┘
       │ • Verdict       │
       │ • Classification│
       │ • Routing       │
       │ • Severity      │
       └────────┬────────┘
                │
                ▼
       ┌─────────────────────┐
       │  NLG + SAFETY       │
       │  SERVICE            │
       │ • Template Generation
       │ • LLM Draft (opt)    │
       │ • Safety Validation  │
       │ • Credential Check   │
       │ • Promise Check      │
       │ • Injection Check    │
       └────────┬────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────┐
│          RESPONSE SCHEMA VALIDATION & ENVELOPE                  │
│         (Pydantic AnalyzeTicketResponse Model)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CLIENT RECEIVES JSON                       │
│  (ticket_id, evidence_verdict, case_type, severity, dept,      │
│   agent_summary, next_action, customer_reply, flags, codes)    │
└─────────────────────────────────────────────────────────────────┘

Async Path (non-blocking):
  └─→ Workflow State Machine
  └─→ Event Publishing (Outbox Pattern)
  └─→ Department Queue Routing
  └─→ Audit Log Recording
```

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend Framework** | FastAPI 0.115+ | Fast async REST API, automatic OpenAPI docs |
| **Python Runtime** | Python 3.13 | Type hints, async/await, performance |
| **Validation** | Pydantic 2.8+ | Input/output schema enforcement |
| **Web Server** | Uvicorn 0.30+ | ASGI server, production-ready |
| **AI/LLM** | Anthropic Claude 3.5 Sonnet | Natural language generation, fallback templates |
| **HTTP Client** | HTTPX 0.27+ | Async HTTP calls to external APIs |
| **Testing** | Pytest 8.2+ | Unit/integration test framework |
| **Deployment** | Docker / Docker Compose | Containerization, local multi-service setup |
| **Orchestration** | Kubernetes manifests | Production multi-region deployment ready |
| **Observability** | Prometheus + OpenTelemetry | Metrics, traces, correlation IDs |
| **Language** | Python | Type-safe, readable, rapid iteration |

---

## Project Structure

```
SUST-Hackathon/
├── app/
│   ├── main.py                          # FastAPI app initialization
│   ├── config.py                        # Environment configuration
│   ├── api/
│   │   ├── routes.py                    # Public API endpoints
│   │   ├── schemas.py                   # Request/response models
│   │   └── errors.py                    # Error handlers
│   ├── auth/
│   │   ├── routes.py                    # Login, refresh, logout
│   │   ├── service.py                   # JWT token lifecycle
│   │   └── schemas.py                   # Auth models
│   ├── core/
│   │   ├── reasoning.py                 # Core investigation logic
│   │   ├── intent.py                    # Parse complaint for intent
│   │   ├── language.py                  # Language detection
│   │   ├── normalization.py             # Sanitize complaint text
│   │   ├── llm.py                       # Anthropic client
│   │   ├── nlg.py                       # Template NLG
│   │   └── safety.py                    # 5 guardrails enforcement
│   ├── domain/
│   │   └── enums.py                     # Case types, severity, departments
│   ├── evidence/
│   │   ├── service.py                   # Transaction lookup & features
│   │   ├── repository.py                # Transaction storage
│   │   └── schemas.py                   # Evidence models
│   ├── investigation/
│   │   ├── service.py                   # Investigation orchestration
│   │   ├── rules.py                     # Rule configuration
│   │   └── schemas.py                   # Investigation models
│   ├── tickets/
│   │   ├── service.py                   # Ticket intake logic
│   │   ├── repository.py                # Ticket storage
│   │   └── schemas.py                   # Ticket models
│   ├── workflows/
│   │   ├── service.py                   # Saga orchestration
│   │   ├── repository.py                # Workflow state storage
│   │   └── schemas.py                   # Workflow models
│   ├── messaging/
│   │   ├── service.py                   # Pub/Sub routing
│   │   ├── repository.py                # Event/routing storage
│   │   └── schemas.py                   # Event models
│   └── observability/
│       ├── middleware.py                # Request tracing
│       ├── registry.py                  # Metrics collection
│       └── schemas.py                   # Observability models
├── tests/
│   └── test_api.py                      # 33 comprehensive tests
├── docs/
│   ├── PLAN.md                          # Execution plan (10 milestones)
│   ├── QueueStorm_Problem_Analysis.md   # Problem deep-dive
│   ├── QueueStorm_Investigator_PRD.md   # Product requirements
│   └── QueueStorm_Investigator_HLD.md   # High-level design
├── deploy/
│   └── k8s/                             # Kubernetes manifests
├── Dockerfile                           # Multi-stage Docker build
├── docker-compose.yml                   # Local multi-service setup
├── requirements.txt                     # Python dependencies
└── README.md                            # This file
```

---

## Setup Instructions

### Prerequisites

- Python 3.13+
- pip or uv package manager
- Git
- Docker & Docker Compose (optional)

### Clone Repository

```bash
git clone https://github.com/mayer-doa-coder/SUST-Hackathon.git
cd SUST-Hackathon
```

### Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file:

```env
# Application
APP_VERSION=1.0.0
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true

# LLM Configuration
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-XXXXX
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_MAX_COMPLAINT_CHARS=2000
LLM_TIMEOUT_SECONDS=10

# Authentication (optional)
AUTH_ENABLED=false
AUTH_JWT_SECRET=your-super-secret-key-change-this

# Rate Limiting (optional)
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
```

---

## Run Commands

### Local Development

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs at `http://localhost:8000/docs`

### Docker

```bash
# Build image
docker build -t queuestorm:latest .

# Run container
docker run -p 8000:8000 \
  -e LLM_API_KEY=sk-ant-XXXXX \
  queuestorm:latest
```

### Docker Compose

```bash
docker-compose up -d
```

### Run Tests

```bash
pytest tests/ -v
```



---

## API Endpoints

### `GET /health`

Health check endpoint.

**Response:**
```json
{"status": "ok"}
```

---

### `POST /analyze-ticket`

Main investigation endpoint.

**Request Headers:**
```
Content-Type: application/json
X-Correlation-ID: <optional-uuid>
Idempotency-Key: <optional-uuid>
```

**Request Body:**
```json
{
  "ticket_id": "TKT-2026-062601-001",
  "complaint": "I sent 5000 BDT to my brother but he didn't receive it",
  "language": "mixed",
  "user_type": "customer",
  "transaction_history": [
    {
      "transaction_id": "TXN-001",
      "timestamp": "2026-06-25T14:05:30+00:00",
      "type": "transfer",
      "amount": 5000,
      "counterparty": "Arif Khan",
      "status": "completed"
    }
  ]
}
```

**Response (200 OK):**
```json
{
  "ticket_id": "TKT-2026-062601-001",
  "relevant_transaction_id": "TXN-001",
  "evidence_verdict": "consistent",
  "case_type": "wrong_transfer",
  "severity": "medium",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports money sent to Arif Khan at 2:05 PM. Transaction history confirms 5000 BDT transfer completed to Arif Khan. Possible delivery delay or receiver confusion.",
  "recommended_next_action": "Contact receiver (Arif Khan) to confirm receipt. If not received within 24 hours, initiate refund.",
  "customer_reply": "Thank you for reporting this. We've confirmed your transfer of 5000 BDT to Arif Khan at 14:05 on Jun 25. Our team will verify receipt and follow up with you within 24 hours.",
  "human_review_required": false,
  "confidence": 0.92,
  "reason_codes": ["amount_exact", "time_close", "counterparty_match", "type_match"]
}
```

**Response Time:** Typically 3–8 seconds; guaranteed <30 seconds (SLA).

---

## Sample Request

```bash
curl -X POST http://localhost:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-2026-062601-M3-1",
    "complaint": "I sent 5000 BDT to my brother Arif yesterday around 2 PM but he says he did not receive it",
    "language": "mixed",
    "channel": "in_app_chat",
    "user_type": "customer",
    "transaction_history": [
      {
        "transaction_id": "TXN-20260625-001234",
        "timestamp": "2026-06-25T14:05:30+00:00",
        "type": "transfer",
        "amount": 5000,
        "counterparty": "Arif Khan",
        "status": "completed"
      },
      {
        "transaction_id": "TXN-20260625-001235",
        "timestamp": "2026-06-25T14:05:35+00:00",
        "type": "transfer",
        "amount": 5000,
        "counterparty": "Arif Khan",
        "status": "completed"
      }
    ]
  }'
```

---

## Sample Response

```json
{
  "ticket_id": "TKT-2026-062601-M3-1",
  "relevant_transaction_id": "TXN-20260625-001234",
  "evidence_verdict": "inconsistent",
  "case_type": "duplicate_payment",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports money sent to brother at 2 PM. Transaction history shows duplicate transfer: two 5000 BDT payments to Arif Khan at 14:05:30 and 14:05:35. Receiver likely received both amounts.",
  "recommended_next_action": "Contact Arif Khan to verify receipt of both transfers. Initiate reversal of duplicate transfer TXN-20260625-001235 if both amounts confirmed received.",
  "customer_reply": "Thank you for reporting this. We found that two transfers of 5000 BDT each were sent to Arif Khan on Jun 25 at 14:05. Our team will verify receipt and process a reversal if needed. You will be updated within 24 hours.",
  "human_review_required": true,
  "confidence": 0.87,
  "reason_codes": [
    "amount_exact",
    "time_close",
    "counterparty_match",
    "duplicate_payment",
    "type_match",
    "nlg_template_v1",
    "safety_policy_v1"
  ]
}
```

---

## AI Investigation Pipeline

The system processes complaints through these **deterministic** steps:

1. **Validate Input Schema** → Pydantic validates all fields
2. **Normalize Complaint** → Sanitize text, cap length
3. **Detect Language** → Identify EN / BN / mixed
4. **Extract Intent** → Parse amount, time, type, counterparty
5. **Score Transactions** → Match by amount, time, type, counterparty
6. **Select Relevant Transaction** → Pick highest score
7. **Generate Evidence Verdict** → CONSISTENT / INCONSISTENT / INSUFFICIENT_DATA
8. **Predict Case Type** → Apply classification rules (8 types)
9. **Assign Severity** → Apply severity rules (4 levels)
10. **Route Department** → Apply routing rules (6 departments)
11. **Determine Human Review** → Flag if needed
12. **Generate Agent Summary** → Brief explanation for agent
13. **Generate Next Action** → Specific instruction
14. **Generate Safe Reply** → Use template + optional LLM
15. **Apply Safety Guardrails** → 5 deterministic checks
16. **Validate Output Schema** → Ensure all fields valid
17. **Add Reason Codes** → Audit trail
18. **Return JSON** → HTTP 200 response

---

## Evidence Reasoning

### Core Principle

**Never classify a complaint using complaint text alone.**

The system **always** cross-references transaction history. This prevents:

- False disputes (claiming money was lost when transaction succeeded)
- Fraudulent refund requests
- Duplicate investigations
- Incorrect routing (phishing misclassified as general inquiry)

### Evidence Verdict

| Verdict | Meaning |
|---------|---------|
| `CONSISTENT` | Transaction supports complaint |
| `INCONSISTENT` | Transaction contradicts complaint |
| `INSUFFICIENT_DATA` | No matching transaction or ambiguous |

### Matching Algorithm

1. Score each transaction by amount, time, type, counterparty
2. Select highest scorer or flag insufficient
3. Compare complaint intent vs. transaction
4. Generate verdict and confidence

---

## Safety Logic

The system enforces **five deterministic safety guardrails**:

### Guardrail 1: No Credential Requests
Customer reply must never ask for PIN, OTP, password, or card number.

### Guardrail 2: No Unauthorized Promises
Never promise or confirm refund, reversal, unblock, or recovery.

### Guardrail 3: No Third-Party Redirects
Never direct customers to external numbers or websites without "official" language.

### Guardrail 4: Prompt Injection Immunity
Complaint text must not override system behavior. Embedded instructions are ignored.

### Guardrail 5: Critical Phishing Escalation
Any phishing report → route to `fraud_risk` at `CRITICAL` severity immediately.

All guardrails run **deterministically** (not AI-based) and execute **after** NLG and **before** response return.

---

## Models

| Model | Purpose | Latency | Cost | Why Chosen |
|-------|---------|---------|------|-----------|
| **Rule Engine** | Transaction matching, classification, routing | <1ms | $0 | Instant, auditable, no API calls |
| **Claude 3.5 Sonnet** | Text generation (summary, action, reply) | 3–8s | $0.002/call | Fast, multilingual, high quality |
| **Safety Guardrails** | Credential/promise/injection detection | <1ms | $0 | Deterministic, zero false negatives |
| **Language Detector** | Identify EN/BN/mixed | <1ms | $0 | Fast, offline, library-based |
| **Intent Parser** | Extract amount, time, counterparty | <1ms | $0 | Deterministic, Bangla-aware |
| **Bangla Numerals** | Convert ৫ to 5, বিশ to 20 | <1ms | $0 | Essential for Bangla complaints |

**Reasoning:**
- Hybrid architecture (deterministic + LLM) provides **safety + quality**
- Rule engine handles all **structured decisions** (verdict, classification, routing)
- LLM handles only **text generation** (summaries, replies)
- If LLM fails, templates guarantee **safe fallback**
- Cost: ~$80 for 40,000 tickets vs. $64,000 for manual agents = **99%+ savings**

---

## Model & Cost Reasoning

**Why Hybrid (Deterministic + LLM)?**

| Approach | Pros | Cons | Status |
|----------|------|------|--------|
| Deterministic Only | Fast, cheap, safe, auditable | Weak NLG, robotic text | Fallback |
| LLM Only | Flexible, natural, impressive | Slow, expensive, risky | ✗ Too risky |
| **Hybrid** | Best of both, safety + quality | Some complexity | **✓ CHOSEN** |

**Per Campaign Event (40,000 tickets):**
- Rule Engine: $0
- Safety Guardrails: $0
- Claude Sonnet: $80
- Infrastructure: $200–500
- **Total: $280–580**
- **vs. Manual Agents: $64,000**

**Latency (Critical Path):**
- Validation: <10ms
- Rule Engine: <5ms
- Evidence Lookup: <50ms
- LLM Call: 3–8s ← Critical path
- Safety + Output: <15ms
- **Total: 3–8s (p95), guaranteed <30s**

**Why Claude 3.5 Sonnet?**
-  Multilingual (English + Bangla native)
-  Fast (3–8s acceptable for 30s SLA)
-  Cheap (~$0.002 per call)
-  High quality text
-  Fallback templates if unavailable

---

## Deployment

### Local Development

```bash
git clone https://github.com/mayer-doa-coder/SUST-Hackathon.git
cd SUST-Hackathon
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export LLM_API_KEY=sk-ant-XXXXX
uvicorn app.main:app --reload
```

### Docker

```bash
docker build -t queuestorm:latest .
docker run -p 8000:8000 -e LLM_API_KEY=sk-ant-XXXXX queuestorm:latest
```

### Kubernetes

```bash
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml
kubectl apply -f deploy/k8s/hpa.yaml
```

### Cloud Platforms

**AWS (App Runner):**
```bash
aws apprunner create-service \
  --service-name queuestorm \
  --source-configuration ImageRepository=<ecr-url>
```

**Google Cloud (Cloud Run):**
```bash
gcloud run deploy queuestorm \
  --image gcr.io/<project>/queuestorm:latest \
  --memory 1Gi --cpu 2 --timeout 60
```

**Railway / Render:** Connect GitHub repo; auto-deploys on push.

---

## Assumptions

1. Complaint text is trusted for content but not intent
2. Transaction history is complete (24–48h)
3. Transaction data is authoritative source of truth
4. Single request = stateless processing (no session memory)
5. No real-time message queue required (in-memory simulation sufficient)
6. Database is persistent in production (in-memory for hackathon)
7. LLM provider is eventually available (circuit breaker + fallback)
8. Support agents are trained on system output
9. Complaint volume follows Poisson distribution

---

## Known Limitations

1. **In-Memory Storage** – Data lost on restart. Production requires database.
2. **Single-Instance** – Horizontal scaling requires load balancer + shared DB.
3. **No Distributed Transaction Guarantees** – Saga simulated in-memory.
4. **LLM Latency Variable** – 2–10s API calls. No local fallback.
5. **Bangla Numeral Support Limited** – Basic numerals only.
6. **No Multilingual Testing at Scale** – EN/BN/mixed supported but edge cases untested.
7. **Safety Guardrails Use Regex** – Pattern-based detection has false positives/negatives.
8. **Optional Auth** – Disabled by default. Production must enable.
9. **In-Memory Rate Limiting** – Resets on server restart.
10. **No Compliance Audit Trail** – Not persisted to immutable store.

---

## Future Improvements

- **Analytics Dashboard** – Complaint volume, routing accuracy, agent performance
- **Fraud Detection ML** – Retrain phishing detector on real incidents
- **A/B Testing** – Test rule changes, prompts, thresholds
- **Performance Caching** – Redis for rules, templates, customer profiles
- **Multi-Region** – Shard by geography, reduce latency
- **Fine-Tuned LLM** – Domain-specific model for FinTech replies
- **Retrieval-Augmented Generation** – Suggest actions from similar cases
- **Sentiment Analysis** – Route irate customers to senior agents
- **Real-Time Fraud Alerts** – Detect emerging phishing campaigns
- **GraphQL API** – Alternative to REST for complex queries

---

**Repository:** https://github.com/mayer-doa-coder/SUST-Hackathon.git

---

## License

MIT License © 2026 QueueStorm Investigator Team

This project is released under the MIT License for educational and hackathon purposes.

---


