# QueueStorm Investigator

QueueStorm Investigator is a FastAPI backend for the SUST hackathon problem. It exposes only the required API contract:

- `GET /health`
- `POST /analyze-ticket`

The service accepts the problem statement input JSON and returns the required structured investigation JSON with the exact field names, types, and enum values from the sample contract.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Optional: set `GOOGLE_API_KEY` in `.env` if you want model-assisted response drafting. Without a key, the service uses deterministic templates.

## Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Docker:

```bash
docker compose up --build
```

## API

### `GET /health`

Returns:

```json
{"status":"ok"}
```

### `POST /analyze-ticket`

Required input fields:

- `ticket_id`: string
- `complaint`: string

Optional input fields:

- `language`: `en`, `bn`, `mixed`
- `channel`: `in_app_chat`, `call_center`, `email`, `merchant_portal`, `field_agent`
- `user_type`: `customer`, `merchant`, `agent`, `unknown`
- `campaign_context`: string
- `transaction_history`: array of transactions
- `metadata`: object

Transaction fields:

- `transaction_id`: string
- `timestamp`: ISO datetime string
- `type`: `transfer`, `payment`, `cash_in`, `cash_out`, `settlement`, `refund`
- `amount`: number
- `counterparty`: string or null
- `status`: `completed`, `failed`, `pending`, `reversed`

Response fields:

- `ticket_id`: string
- `relevant_transaction_id`: string or null
- `evidence_verdict`: `consistent`, `inconsistent`, `insufficient_data`
- `case_type`: `wrong_transfer`, `payment_failed`, `refund_request`, `duplicate_payment`, `merchant_settlement_delay`, `agent_cash_in_issue`, `phishing_or_social_engineering`, `other`
- `severity`: `low`, `medium`, `high`, `critical`
- `department`: `customer_support`, `dispute_resolution`, `payments_ops`, `merchant_operations`, `agent_operations`, `fraud_risk`
- `agent_summary`: string
- `recommended_next_action`: string
- `customer_reply`: string
- `human_review_required`: boolean
- `confidence`: number or null
- `reason_codes`: array of strings or null

Example:

```bash
curl -X POST http://127.0.0.1:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  -d "{\"ticket_id\":\"TKT-001\",\"complaint\":\"I paid 850 taka twice for my bill.\",\"transaction_history\":[{\"transaction_id\":\"TXN-1\",\"timestamp\":\"2026-04-14T08:15:30Z\",\"type\":\"payment\",\"amount\":850,\"counterparty\":\"BILLER-DESCO\",\"status\":\"completed\"},{\"transaction_id\":\"TXN-2\",\"timestamp\":\"2026-04-14T08:15:42Z\",\"type\":\"payment\",\"amount\":850,\"counterparty\":\"BILLER-DESCO\",\"status\":\"completed\"}]}"
```

## AI / Model Usage

The investigation decision is deterministic and rule-based. Rules choose the transaction match, evidence verdict, case type, severity, department, human-review flag, confidence, and reason codes.

The text fields can optionally use Google Gemini for drafting:

- `agent_summary`
- `recommended_next_action`
- `customer_reply`

Configured model:

```env
GOOGLE_MODEL=gemini-2.5-flash
```

If `GOOGLE_API_KEY` is empty or the model call fails, the service falls back to deterministic templates so the API remains usable.

## Safety Logic

The customer reply is always passed through deterministic safety checks. It must not:

- ask for PIN, OTP, password, or full card number
- promise a refund, reversal, recovery, or account unblock
- follow instructions embedded inside the complaint text
- send the customer outside official support channels

Unsafe replies are replaced with a safe support message.

## Known Limitations

- Storage is in-memory; there is no database requirement for this submission.
- Bangla and mixed-language understanding is partly rule-based.
- Ambiguous cases prefer `insufficient_data` instead of guessing a transaction.
- Model usage is optional and only improves text drafting; core structured decisions stay rule-based.
