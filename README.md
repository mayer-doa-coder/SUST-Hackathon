# QueueStorm Investigator

QueueStorm Investigator is a FastAPI backend that investigates support complaints against supplied transaction history and returns a safe, structured JSON response for support agents.

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /health`
- `POST /analyze-ticket`

## AI Approach

- Deterministic rule engine owns all scored structured fields.
- Optional Anthropic NLG improves `agent_summary`, `recommended_next_action`, and `customer_reply`.
- If no LLM key is configured or the LLM fails, the service falls back to deterministic templates.

## Safety Logic

- Never requests PIN, OTP, password, or card number.
- Never promises refund, reversal, recovery, or account unblock.
- Never trusts complaint text as instructions.
- Runs deterministic safety enforcement after text generation.

## MODELS

- Primary optional model: `claude-haiku-4-5-20251001`
- Runtime: external API only
- Reason chosen: low latency and acceptable multilingual/NLG quality

## Known Limitations

- Bangla and mixed-language extraction is partially rule-based and may be less nuanced than a fully tuned multilingual system.
- The service intentionally prefers `insufficient_data` over guessing in ambiguous cases.
- Heavyweight infra from the HLD is intentionally deferred for the preliminary round.

## Sample Output

- See `sample_output.json`

