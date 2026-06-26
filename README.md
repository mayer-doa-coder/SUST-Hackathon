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
- `GET /analysis/{case_id}`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/jwks`
- `POST /tickets/analyze`
- `GET /tickets/{case_id}`
- `GET /tickets/{case_id}/status`
- `GET /transactions/{transaction_id}`
- `GET /accounts/{account_id}/transactions`
- `POST /evidence/features`
- `POST /investigations/evaluate`
- `GET /rules/active-version`
- `POST /nlg/draft`
- `POST /safety/validate`
- `POST /workflows/analyze-ticket/start`
- `POST /workflows/{case_id}/steps/evidence-complete`
- `POST /workflows/{case_id}/steps/investigation-complete`
- `POST /workflows/{case_id}/steps/nlg-complete`
- `POST /workflows/{case_id}/compensate`
- `POST /workflows/{case_id}/retry`
- `GET /workflows/{case_id}`
- `POST /events/publish`
- `GET /audit/events`
- `GET /audit/events/{case_id}`
- `GET /routing/departments/{department}/cases`
- `GET /events/dead-letter`
- `GET /platform/scaling-plan`
- `GET /platform/database-route`
- `GET /platform/transaction-shards/{account_id}`
- `GET /ready`
- `GET /metrics`
- `GET /observability/health`
- `GET /observability/traces`

## Gateway, Auth, and Rate Limiting

- The API gateway adds `X-Correlation-ID` to every response.
- Set `AUTH_REQUIRED=true` to require bearer JWTs for gateway analysis endpoints.
- Use `/auth/login` with the configured demo credentials to issue access and refresh tokens.
- Set `RATE_LIMIT_ENABLED=true` to enable the current in-memory rate limiter.
- Redis-backed distributed rate limiting is the intended production backend for the multi-server plan.

## Ticket Intake Service

- The gateway forwards analysis requests to the Ticket Intake Service boundary.
- Ticket Intake records case status, supports `Idempotency-Key`, and writes outbox-style workflow events.
- The current repository is in-memory so the project stays runnable; the service boundary is ready for a PostgreSQL primary/read-replica implementation.

## Transaction Evidence Service

- Evidence owns transaction lookup, account transaction read models, compact feature extraction, and shard routing.
- The current implementation uses an in-memory shard-aware repository plus cache-aside behavior.
- Production storage is intended to be sharded PostgreSQL/Citus, distributed SQL, or another horizontally scalable transaction store with read replicas.

## Investigation Service

- Investigation owns deterministic structured decisions: transaction match, verdict, case type, severity, department, and human review.
- Rules are exposed through `GET /rules/active-version` with cache status and version metadata.
- `POST /investigations/evaluate` returns decision fields only; NLG remains outside this service boundary.

## NLG and Safety Service

- `POST /nlg/draft` generates agent summary, recommended action, and customer reply from rule-owned facts.
- `POST /safety/validate` enforces deterministic customer-reply safety and replaces unsafe text.
- Prompt, template, and safety policy versions are configurable through environment variables.
- If no LLM key is configured, NLG uses safe deterministic templates.

## Case Orchestration Service

- Workflows use a Saga-style state machine with idempotent step events.
- Supported steps are evidence, investigation, and NLG.
- Workflows end as completed, failed, compensated, or manual-review-ready in later milestones.
- Ticket Intake starts and completes the workflow during the current synchronous analysis path.

## Pub/Sub, Audit, and Routing

- Published events use a versioned envelope with event id, case id, correlation id, timestamp, and schema version.
- The in-memory broker records audit events, supports idempotent replay, and keeps a dead-letter list.
- Completed ticket-analysis events route cases to department queues such as fraud risk, payments ops, and dispute resolution.
- Ticket Intake publishes its outbox events into this broker in the runnable local implementation.

## Performance and Scaling

- `GET /platform/scaling-plan` exposes the planned replica counts, load-balancer scopes, DB scaling model, cache policy, shard strategy, and load-test target.
- `GET /platform/database-route?operation=read|write` shows read-replica vs primary routing behavior.
- `GET /platform/transaction-shards/{account_id}` returns deterministic shard routing for transaction evidence.
- A smoke load-test scaffold is available at `scripts/load_test_smoke.py`.

Example:

```bash
python scripts/load_test_smoke.py --base-url http://127.0.0.1:8000 --requests 20 --workers 4
```

## Observability and Deployment

- `/ready` returns component-level readiness.
- `/metrics` exposes Prometheus-style request counters and average latency gauges.
- `/observability/traces` shows recent request traces with correlation IDs.
- `docker-compose.yml` provides a local multi-service deployment shape with Postgres and Redis.
- Kubernetes scaffolding lives in `deploy/k8s/`.
- Operational notes live in `docs/RUNBOOK.md`.

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
- Distributed infrastructure integrations are represented by local service boundaries and in-memory adapters; production deployments should replace them with managed Postgres/read replicas, Redis, and Kafka/RabbitMQ.

## Sample Output

- See `sample_output.json`

