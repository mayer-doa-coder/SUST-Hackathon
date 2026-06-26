# QueueStorm Investigator Distributed Architecture Execution Plan

## 1. Executive Summary

### Product Understanding
QueueStorm Investigator is an internal support copilot for a Bangladesh digital finance platform under campaign surge conditions. Its job is to investigate a complaint against supplied transaction history, determine what the evidence supports, classify and route the case safely, and draft support-ready language.

### Target Architecture Direction
This plan uses a microservice architecture with multiple deployable servers, separate data ownership per service, load balancing, caching, message queues, read/write database separation, replication, sharding, rate limiting, JWT-based authentication, API gateway/proxy routing, and distributed transaction patterns.

The architecture is designed around these core scaling challenges:
- Too many concurrent users during campaign surges.
- Too much transaction and audit data to move around synchronously.
- The system must be fast and responsive for support agents.
- Some states may be temporarily inconsistent because distributed systems favor availability in selected paths.
- Financial-support decisions require safety, traceability, and controlled escalation.

### High-Level Service Map
- API Gateway / Reverse Proxy: public entry point, TLS termination, routing, JWT validation, rate limiting, request correlation.
- Auth Service: login, JWT generation, token refresh, role claims, key rotation.
- Ticket Intake Service: validates `/analyze-ticket`, stores ticket metadata, starts analysis workflow.
- Investigation Service: deterministic evidence reasoning, transaction matching, classification, severity, department routing.
- Transaction Evidence Service: owns transaction lookup, read models, partitioned transaction access, fraud/duplicate signals.
- NLG and Safety Service: LLM/template generation, Bangla/English replies, deterministic safety enforcement.
- Case Orchestration Service: coordinates distributed workflow through Saga orchestration and exposes workflow status.
- Audit Service: immutable decision/event log for compliance and debugging.
- Notification/Routing Service: publishes routed cases to dispute, payments, merchant ops, agent ops, or fraud risk queues.
- Observability Service Stack: logs, metrics, traces, dashboards, alerts.

### Data Ownership Summary
- Auth Service: PostgreSQL for users, roles, refresh tokens, signing key metadata.
- Ticket Intake Service: PostgreSQL primary for ticket records, read replica for agent queries.
- Investigation Service: PostgreSQL or embedded rule configuration store; Redis for hot rule/config cache.
- Transaction Evidence Service: sharded PostgreSQL or distributed SQL for transaction metadata; optional object storage for bulk history; Redis for recent transaction cache.
- NLG and Safety Service: PostgreSQL for prompt/template versions and safety policy versions; Redis for provider circuit state.
- Audit Service: append-only event store using Kafka plus long-term object storage or ClickHouse/OpenSearch for querying.
- Notification Service: Kafka topics or RabbitMQ exchanges for department routing.

### Trust Boundary
- Deterministic services own structured decisions: transaction id, evidence verdict, case type, severity, department, human review.
- NLG owns only text fields: `agent_summary`, `recommended_next_action`, `customer_reply`.
- Safety enforcement runs after NLG and before the final response/event is committed.
- Complaint text is untrusted input and cannot override system behavior.

### CAP Theorem Position
- Auth, ticket creation, final decision records, and audit writes favor consistency over availability where correctness matters.
- Transaction read models, dashboards, notifications, and cached case status favor availability and partition tolerance with eventual consistency.
- Agent-facing analysis uses a bounded-consistency approach: return the best available validated decision quickly, while asynchronous events repair or enrich non-critical state.

---

## 2. Architecture Review

### Chosen Architecture Pattern
- Microservices with clear bounded contexts.
- API Gateway / proxy pattern for a single external contract.
- Database-per-service ownership.
- CQRS for high-volume read paths.
- Saga pattern for distributed transactions.
- Event-driven integration through Kafka/RabbitMQ.
- Cache-aside pattern for hot reads.
- Read replicas and sharding for scalable data access.
- Horizontal autoscaling behind load balancers.

### Why Microservices Fit This Version
- Campaign traffic can scale individual services independently.
- Transaction lookup load is separated from NLG latency.
- Safety and compliance logging can evolve independently.
- Multiple teams can own API/platform, evidence reasoning, AI/safety, and infrastructure.
- Failures can be isolated: if NLG is slow, deterministic structured analysis can still complete with templates.

### Main Distributed-System Risks
- Cross-service latency can exceed the request timeout.
- Eventual consistency can show outdated case states.
- Distributed transactions are harder than local commits.
- More services increase operational burden.
- Cache invalidation and replica lag can affect evidence freshness.
- Misconfigured rate limits can block legitimate support traffic.

### Design Responses
- Keep synchronous path narrow: gateway -> intake -> investigation -> evidence -> safety/NLG.
- Move audit, notifications, analytics, and department routing to async events.
- Use Saga orchestration for multi-step case creation and routing.
- Use idempotency keys on write endpoints.
- Use outbox pattern for reliable event publication.
- Use circuit breakers, request deadlines, retries with backoff, and fallback templates.
- Use correlation IDs across all service logs, events, and traces.

---

## 3. Evaluation Strategy

### Highest-Value Technical Outcomes
- API contract remains stable behind the gateway.
- Structured evidence reasoning remains deterministic and testable.
- Safety enforcement remains deterministic and centralized.
- System survives high concurrency using load balancing, caching, queues, and horizontal scaling.
- Read-heavy data paths are separated from write-heavy paths.
- Distributed workflows are observable, retryable, and idempotent.

### Mandatory Items
- `GET /health` at the gateway and each service.
- `POST /analyze-ticket` exposed by the gateway.
- JWT issuance and validation.
- Rate limiting at the gateway.
- Service-to-service authentication.
- Per-service database ownership.
- Cache strategy for hot transaction/rule reads.
- Message queue or pub/sub integration for audit and routing.
- Read/write separation for ticket and transaction stores.
- Replication and sharding plan for high-volume transaction data.
- Saga or outbox-based distributed transaction design.

### Common Failure Points
- Gateway schema differs from internal service schema.
- Services share databases directly instead of using APIs/events.
- Synchronous calls fan out too widely.
- Read replicas serve stale state without clear UI/status semantics.
- Kafka/RabbitMQ events are published without idempotency.
- Cache returns stale rule or transaction state without versioning.
- JWT is generated but not validated consistently across services.

---

## 4. Implementation Roadmap

### Milestone 1: API Gateway, Proxy, and Contract Boundary
- Goal: expose a single stable external API while routing internally to microservices.
- Why: the gateway protects clients from service layout changes and enables centralized traffic controls.
- Business value: support agents and judges use one endpoint even as the backend scales horizontally.
- Components: API gateway, reverse proxy, route mapping, request/response schema validation, correlation ID middleware, gateway health endpoint.
- Database choice: none; gateway remains stateless.
- Scaling design: multiple gateway replicas behind a cloud load balancer or NGINX/Envoy/Traefik.
- Endpoints: `GET /health`, `POST /analyze-ticket`, `GET /analysis/{case_id}`.
- Deliverables: gateway service, OpenAPI contract, routing to ticket intake service, centralized error envelope.
- Testing strategy: contract tests, malformed request tests, upstream timeout tests, correlation ID propagation tests.
- Acceptance criteria: gateway validates input, proxies valid requests, returns controlled errors, and can run multiple replicas.
- Risks: gateway becomes too smart.
- Mitigation: keep business logic in downstream services.

### Milestone 2: Auth Service, JWT Generation, and Rate Limiting
- Goal: protect APIs with JWT authentication and traffic throttling.
- Why: internal financial-support tools require identity, authorization, and abuse protection.
- Business value: prevents unauthorized access and protects the platform during surges.
- Components: login endpoint, JWT generation, refresh-token flow, role claims, signing key rotation, gateway JWT validation, per-user/per-IP/per-role rate limits.
- Database choice: PostgreSQL primary for users, roles, refresh tokens, and key metadata; read replica for user/session lookups if needed.
- Cache choice: Redis for token denylist, rate-limit counters, and short-lived session metadata.
- Scaling design: stateless auth replicas behind internal load balancer; Redis cluster for rate-limit scale.
- Endpoints: `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/jwks`.
- Deliverables: signed JWTs, gateway validation, role-based access control, rate-limit headers.
- Testing strategy: expired token, invalid signature, revoked token, role denial, burst traffic, distributed rate-limit consistency.
- Acceptance criteria: protected endpoints reject invalid tokens and throttle excess requests without blocking normal support usage.
- Risks: Redis outage impacts login/rate limiting.
- Mitigation: fail closed for auth validation, fail with conservative local limits for rate limiting.

### Milestone 3: Ticket Intake Service and Write Model
- Goal: accept analysis requests, persist ticket metadata, and create an idempotent workflow.
- Why: campaign surges require reliable request acceptance even when downstream services are slower.
- Business value: no complaint is lost during traffic spikes.
- Components: request validation, idempotency key handling, ticket write model, outbox table, workflow-start event.
- Database choice: PostgreSQL primary for ticket writes; read replica for agent-facing ticket queries.
- Read/write separation: all writes go to primary; status/detail queries prefer replicas with fallback to primary for read-your-write cases.
- Scaling design: stateless ticket intake replicas; PostgreSQL primary with read replicas; connection pooler such as PgBouncer.
- Endpoints: `POST /tickets/analyze`, `GET /tickets/{case_id}`, `GET /tickets/{case_id}/status`.
- Message queue: publish `TicketAnalysisRequested` through outbox to Kafka/RabbitMQ.
- Deliverables: durable case id, persisted request envelope, idempotent duplicate handling.
- Testing strategy: duplicate request tests, concurrent same-idempotency-key tests, replica-lag behavior tests.
- Acceptance criteria: repeated requests do not create duplicate cases and workflow events are eventually published exactly once logically.
- Risks: database primary bottleneck.
- Mitigation: partition tickets by date or tenant, use connection pooling, batch outbox publishing.

### Milestone 4: Transaction Evidence Service with Sharding, Replication, and Cache
- Goal: provide fast transaction lookup and evidence features at high volume.
- Why: transaction data is the largest and hottest data source during complaint surges.
- Business value: faster evidence matching and lower load on the source ledger.
- Components: transaction lookup API, recent transaction cache, read-optimized indexes, duplicate-payment query, established-recipient query.
- Database choice: sharded PostgreSQL/Citus, CockroachDB/YugabyteDB, or DynamoDB-style partitioned store for transaction metadata.
- Sharding strategy: shard by `account_id` or customer wallet id; secondary indexes by transaction id and timestamp.
- Replication strategy: primary per shard with read replicas; async replicas for scale; strict primary read when freshness is required.
- Cache choice: Redis cache-aside for recent transactions, transaction id lookups, and hot customer histories.
- Data movement strategy: pass transaction references and compact evidence features, not full transaction histories, between services.
- Endpoints: `GET /transactions/{transaction_id}`, `GET /accounts/{account_id}/transactions`, `POST /evidence/features`.
- Testing strategy: hot-account load tests, cache hit/miss tests, replica-lag tests, shard-routing tests.
- Acceptance criteria: service returns evidence features within latency budget and handles missing/stale data explicitly.
- Risks: cross-shard queries are expensive.
- Mitigation: avoid global scans, precompute read models, route by account/customer shard key.

### Milestone 5: Investigation Service and Deterministic Rule Engine
- Goal: produce structured investigation decisions without LLM dependency.
- Why: evidence reasoning, routing, and escalation must remain deterministic and auditable.
- Business value: protects correctness for financial support decisions.
- Components: normalization, Bangla numeral handling, intent extraction, transaction matcher, verdict engine, classifier, severity/department router, human-review decision engine.
- Database choice: PostgreSQL for versioned rule configuration and reason-code taxonomy; Redis for active ruleset cache.
- CAP choice: prefer consistency for active rule version reads; fall back to last-known-good ruleset if config DB is unavailable.
- Scaling design: stateless investigation replicas behind internal load balancer.
- Endpoints: `POST /investigations/evaluate`, `GET /rules/active-version`.
- Deliverables: structured decision object with rule version, confidence/reason codes, and evidence references.
- Testing strategy: public samples, ambiguity tests, no-match tests, duplicate-payment tests, phishing override tests, Bangla numeral tests.
- Acceptance criteria: structured fields are rule-owned and deterministic across replicas.
- Risks: stale rule cache causes inconsistent outputs.
- Mitigation: ruleset versioning, cache TTL, forced invalidation events, response includes rule version.

### Milestone 6: NLG and Safety Service
- Goal: generate safe agent summaries, recommended next actions, and customer replies.
- Why: response text must be helpful without promising unauthorized outcomes or asking for secrets.
- Business value: agents get usable language while safety remains enforced in code.
- Components: LLM client, template fallback, Bangla/English templates, safety scanner, unsafe-output replacement, provider circuit breaker.
- Database choice: PostgreSQL for prompt versions, template versions, and safety policy versions.
- Cache choice: Redis for provider circuit state and hot templates.
- Scaling design: separate NLG replicas because LLM latency differs from rule-engine latency.
- Endpoints: `POST /nlg/draft`, `POST /safety/validate`.
- Queue option: async `DraftRequested` and `DraftCompleted` events for slower enriched replies.
- Testing strategy: prompt injection tests, OTP/PIN request tests, refund-promise tests, LLM timeout tests.
- Acceptance criteria: unsafe generated text is replaced before final response or event commit.
- Risks: LLM latency slows synchronous API.
- Mitigation: strict deadline, template fallback, circuit breaker, async enrichment path.

### Milestone 7: Case Orchestration and Distributed Transaction API
- Goal: coordinate ticket intake, evidence lookup, investigation, NLG/safety, audit, and routing as one reliable workflow.
- Why: there is no single database transaction across services.
- Business value: cases are not half-created or silently lost when one service fails.
- Pattern: Saga orchestration with idempotent steps and compensating actions.
- Database choice: PostgreSQL for workflow state and step attempts.
- Message queue: Kafka/RabbitMQ topics for workflow events and retries.
- Distributed transaction endpoints:
  - `POST /workflows/analyze-ticket/start`
  - `POST /workflows/{case_id}/steps/evidence-complete`
  - `POST /workflows/{case_id}/steps/investigation-complete`
  - `POST /workflows/{case_id}/steps/nlg-complete`
  - `POST /workflows/{case_id}/compensate`
  - `GET /workflows/{case_id}`
- Consistency design: final case status is eventually consistent; workflow state is the source of truth for progress.
- Deliverables: Saga state machine, retry policies, dead-letter queue, compensation behavior, idempotent step APIs.
- Testing strategy: kill downstream service mid-workflow, duplicate events, out-of-order events, retry exhaustion, compensation tests.
- Acceptance criteria: workflow reaches completed, failed, or manual-review state without duplicate side effects.
- Risks: distributed workflow complexity.
- Mitigation: make steps idempotent, use status transitions, store event ids, define clear terminal states.

### Milestone 8: Message Queue, Pub/Sub, Audit, and Department Routing
- Goal: move non-blocking work off the synchronous request path.
- Why: audit, notifications, analytics, and department routing should not slow the agent response.
- Business value: high responsiveness during campaign traffic.
- Components: Kafka/RabbitMQ, topics/exchanges, consumers, outbox publishers, dead-letter queues, audit writer, department routing consumers.
- Database choice: Kafka as event log; ClickHouse/OpenSearch for searchable audit and operational analytics; object storage for long-term archive.
- Topics/events: `TicketAnalysisRequested`, `EvidenceCollected`, `InvestigationCompleted`, `SafetyValidated`, `CaseRouted`, `AuditRecorded`, `WorkflowFailed`.
- Scaling design: partition topics by `case_id` or tenant; scale consumers by consumer group.
- Testing strategy: event replay, duplicate event handling, consumer lag, dead-letter processing.
- Acceptance criteria: all decisions are auditable and route events survive service restarts.
- Risks: queue lag during traffic spikes.
- Mitigation: partitioning, autoscaled consumers, backpressure, prioritized fraud/safety topics.

### Milestone 9: Performance, Load Balancing, and Database Scaling
- Goal: prove the system handles high concurrency and large data volume.
- Why: campaign surges are the central operational challenge.
- Business value: support agents receive fast responses instead of waiting behind overloaded services.
- Components: external load balancer, internal service load balancing, autoscaling policies, DB connection pooling, read replicas, shard routing, cache warming, CDN only for static docs if needed.
- Database scaling:
  - Auth: primary plus read replica.
  - Tickets: primary plus read replicas, partition by creation date/tenant.
  - Transactions: shard by account/customer id, replicate each shard.
  - Audit: append-only event log plus analytics store.
  - Rules/templates: primary plus cache, low write volume.
- Testing strategy: load tests for `POST /analyze-ticket`, hot account tests, queue backpressure tests, cache stampede tests, replica failover tests.
- Acceptance criteria: p95 latency target is met, error rate stays within budget, no database connection exhaustion.
- Risks: bottleneck shifts to evidence or NLG service.
- Mitigation: bulkheads, per-service autoscaling, NLG fallback, evidence cache, queue-based smoothing.

### Milestone 10: Observability, Deployment, and Final Verification
- Goal: deploy a multi-service system that can be operated and debugged.
- Why: distributed systems fail in partial ways and require visibility.
- Business value: faster incident response and safer production operation.
- Components: Docker Compose for local multi-service setup, Kubernetes or VM-based multi-server deployment, Prometheus metrics, Grafana dashboards, OpenTelemetry traces, centralized logs, health/readiness checks.
- Deployment design: gateway on public nodes; internal services on private network; databases managed or dedicated; queues replicated; secrets in environment/secret manager.
- Testing strategy: end-to-end smoke tests, service restart tests, failover tests, secret sweep, JWT validation, safety regression, sample-case parity.
- Acceptance criteria: public gateway is reachable, internal services are healthy, traces show cross-service request flow, dashboards expose latency/error/queue metrics.
- Risks: operational complexity.
- Mitigation: start with Docker Compose, then move to staged deployment; document runbooks and rollback steps.

---

## 5. Dependency Graph

```text
Milestone 1: API Gateway / Proxy
        |
        v
Milestone 2: Auth / JWT / Rate Limiting
        |
        v
Milestone 3: Ticket Intake Write Model
        |
        +-------------------------+
        |                         |
        v                         v
Milestone 4: Transaction       Milestone 6: NLG + Safety
Evidence Service                    ^
        |                            |
        v                            |
Milestone 5: Investigation Rules ----+
        |
        v
Milestone 7: Saga Orchestration
        |
        v
Milestone 8: Pub/Sub + Audit + Routing
        |
        v
Milestone 9: Performance + DB Scaling
        |
        v
Milestone 10: Observability + Deployment
```

Critical request path:

```text
Client
  |
  v
Load Balancer
  |
  v
API Gateway / Proxy / Rate Limit / JWT Validation
  |
  v
Ticket Intake Service
  |
  v
Case Orchestrator
  |
  +--> Transaction Evidence Service --> Sharded Transaction DB + Redis
  |
  +--> Investigation Service ---------> Rules DB + Redis
  |
  +--> NLG and Safety Service --------> LLM/Templates + Safety DB
  |
  +--> Audit/Event Stream ------------> Kafka/RabbitMQ + Audit Store
  |
  v
Response Validation
  |
  v
Client
```

---

## 6. Critical Path

### MUST HAVE
- Gateway/proxy with stable public API.
- Auth service with JWT generation and validation.
- Rate limiting at the gateway.
- Ticket intake service with idempotent write model.
- Investigation service with deterministic structured decisions.
- Transaction evidence service with clear database ownership.
- Safety/NLG service with fallback templates.
- Message queue for audit and routing.
- Basic Saga workflow for distributed transaction handling.

### SHOULD HAVE
- Read replicas for ticket and auth queries.
- Redis cache for recent transactions, rules, templates, and rate limits.
- Outbox pattern for reliable event publication.
- Dead-letter queues and retry policies.
- Service-level health/readiness checks.
- OpenTelemetry tracing across gateway and services.

### NICE TO HAVE
- Full transaction sharding implementation.
- Multi-region replication.
- Advanced autoscaling by queue lag.
- Blue-green or canary deployment.
- Searchable audit dashboards.
- Read model projections for agent dashboards.

### CAP and Consistency Rules
- Strong consistency for auth, ticket creation, final decision writes, and audit event persistence.
- Eventual consistency for department routing, notifications, analytics, and read replicas.
- Bounded staleness for transaction evidence reads; force primary read when a fresh transaction id is explicitly referenced.
- Availability-first behavior for NLG: return safe template fallback if LLM or provider is unavailable.

---

## 7. Engineering Task Breakdown

### Engineer A: Gateway / Auth / Platform Lead
- Build API gateway, proxy routing, JWT validation, rate limits, correlation IDs.
- Build Auth Service endpoints and token lifecycle.
- Own load balancer config, service discovery, deployment topology, and external contract.

### Engineer B: Ticket / Workflow / Distributed Transaction Lead
- Build Ticket Intake Service, idempotency, ticket database schema, read/write separation.
- Build Case Orchestration Service with Saga workflow state.
- Own outbox pattern, workflow retries, compensation endpoints, and workflow status APIs.

### Engineer C: Evidence / Rules Lead
- Build Transaction Evidence Service, transaction cache, shard-routing design, read models.
- Build Investigation Service, deterministic rule engine, Bangla normalization, classification, severity, routing decision.
- Own CAP decisions for evidence freshness and rule consistency.

### Engineer D: AI / Safety / Messaging / Observability Lead
- Build NLG and Safety Service with template fallback and LLM circuit breaker.
- Build Kafka/RabbitMQ topics, audit consumers, department routing consumers, dead-letter queues.
- Own traces, logs, metrics, dashboards, and safety regression tests.

### Parallelization Plan
- A starts gateway/auth while B starts ticket intake and workflow schema.
- C starts evidence/rule services using local mock APIs until gateway routing is ready.
- D starts safety templates and queue/audit contracts.
- Integration order: gateway -> auth -> ticket intake -> evidence -> investigation -> safety/NLG -> orchestration -> pub/sub -> observability -> scaling tests.

---

## 8. Time Allocation

### Architecture-Complete Build Order
- 0:00-0:30 confirm service boundaries, data ownership, event contracts, and endpoint contracts.
- 0:30-1:30 gateway, auth, JWT, rate limiting, and local service discovery.
- 1:30-2:30 ticket intake service, PostgreSQL schema, idempotency, outbox.
- 2:30-3:45 transaction evidence service, cache, shard key design, read/write model.
- 3:45-5:00 investigation service and deterministic rule engine.
- 5:00-6:00 NLG/safety service with fallback and circuit breaker.
- 6:00-7:00 Saga orchestrator and distributed transaction endpoints.
- 7:00-8:00 Kafka/RabbitMQ topics, audit writer, department routing consumers.
- 8:00-9:00 load balancing, replicas, DB scaling configuration, cache tuning.
- 9:00-10:00 observability, end-to-end tests, failure tests, documentation.

### Time-Budget Rule
- If implementation time is limited, keep the gateway, auth, ticket intake, investigation, safety, and basic queue flow first.
- If scaling implementation slips, document sharding/replication choices and implement cache/read-replica hooks.
- If LLM integration slips, keep deterministic templates and safety enforcement.

---

## 9. Agent Mode Prompt Sequence

### Milestone 1 Prompt
"Read the source-of-truth docs and implement the API Gateway / proxy boundary for QueueStorm Investigator. Expose `GET /health`, `POST /analyze-ticket`, and `GET /analysis/{case_id}` at the gateway. Add schema validation, correlation IDs, upstream timeout handling, and route forwarding to the Ticket Intake Service. Keep the gateway stateless and free of business logic."

### Milestone 2 Prompt
"Implement Auth Service and gateway security. Add JWT generation, refresh, logout, JWKS endpoint, gateway JWT validation, role claims, and Redis-backed rate limiting. Use PostgreSQL for users/roles/refresh tokens and Redis for denylist/rate-limit counters. Add tests for invalid tokens, expired tokens, revoked tokens, and burst traffic."

### Milestone 3 Prompt
"Implement Ticket Intake Service. Add durable ticket creation, idempotency keys, PostgreSQL primary write model, read-replica query path, outbox table, and `TicketAnalysisRequested` publication. Expose ticket status APIs and ensure duplicate requests do not create duplicate cases."

### Milestone 4 Prompt
"Implement Transaction Evidence Service. Own transaction lookup APIs, recent transaction cache, shard-key routing design, read replica strategy, duplicate-payment features, and established-recipient features. Avoid moving full histories between services; return compact evidence features and references."

### Milestone 5 Prompt
"Implement Investigation Service with deterministic rules only. Add normalization, Bangla numeral parsing, intent extraction, transaction matching, evidence verdict, case classification, severity, department routing, and human review. Use versioned rule configuration and Redis active-rules cache. Do not let the LLM own structured fields."

### Milestone 6 Prompt
"Implement NLG and Safety Service. Generate `agent_summary`, `recommended_next_action`, and `customer_reply` through safe templates first, then optional LLM. Add deterministic post-generation safety validation, unsafe text replacement, prompt/template versioning, Redis circuit state, and timeout fallback."

### Milestone 7 Prompt
"Implement Case Orchestration Service using Saga orchestration. Add workflow state storage, idempotent step endpoints, retry policy, compensation endpoint, dead-letter handling, and status transitions. Ensure cross-service workflow failures end in completed, failed, or manual-review states without duplicate side effects."

### Milestone 8 Prompt
"Implement pub/sub integration for audit and department routing. Add Kafka/RabbitMQ topics, consumers, outbox publishers, audit storage, route events, dead-letter queues, and replay-safe event handlers. Every emitted event must include case id, correlation id, event id, timestamp, and schema version."

### Milestone 9 Prompt
"Implement performance and scaling configuration. Add load balancer setup, multiple service replicas, DB connection pooling, read/write separation, transaction shard routing, Redis cache policies, backpressure handling, and load tests for high-concurrency `POST /analyze-ticket` traffic."

### Milestone 10 Prompt
"Implement observability and final deployment. Add Docker Compose or Kubernetes manifests, service health/readiness probes, Prometheus metrics, Grafana dashboards, OpenTelemetry traces, centralized logs, secret management notes, and end-to-end failure tests."

---

## 10. Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|---|---|---:|---|
| Gateway bottleneck | Medium | High | Horizontal gateway replicas, external load balancer, lightweight proxy logic |
| Auth/rate-limit Redis outage | Medium | High | Redis cluster, local emergency limits, clear fail-open/fail-closed policy |
| Database primary overload | High | High | Read replicas, partitioning, connection pooling, write batching |
| Transaction data too large to move | High | High | Evidence feature API, shard-local queries, cache-aside recent history |
| Cross-service latency | High | High | Narrow sync path, deadlines, async audit/routing, circuit breakers |
| Eventual consistency confusion | Medium | Medium | Explicit workflow states, read-your-write fallback, UI/status messaging |
| Distributed transaction partial failure | Medium | Critical | Saga orchestration, idempotency, outbox, compensation endpoints |
| Queue lag during campaign surge | Medium | High | Topic partitioning, autoscaled consumers, backpressure, priority queues |
| Cache stale data | Medium | High | TTLs, versioned rules/templates, forced invalidation, primary-read escape hatch |
| Unsafe generated reply | Medium | Critical | Deterministic safety service, replacement templates, regression tests |
| JWT misconfiguration | Medium | Critical | JWKS rotation tests, strict validation, short-lived access tokens |
| Shard hot spot | Medium | High | shard by account/customer id, monitor hot keys, split hot shards |

---

## 11. Pre-Coding Checklist

- [ ] Service boundaries and owners agreed.
- [ ] API Gateway contract locked.
- [ ] Auth/JWT flow and roles defined.
- [ ] Rate-limit policy defined by user/IP/role.
- [ ] Database-per-service ownership agreed.
- [ ] Read/write separation strategy defined.
- [ ] Transaction shard key selected.
- [ ] Replication strategy selected for each database.
- [ ] Cache keys, TTLs, and invalidation policy defined.
- [ ] Queue technology selected: Kafka or RabbitMQ.
- [ ] Event schemas and schema versions defined.
- [ ] Saga workflow states and compensation behavior defined.
- [ ] CAP tradeoffs documented per service.
- [ ] Safety rules translated into deterministic checks.
- [ ] LLM trust boundary agreed.
- [ ] Load balancer and deployment topology selected.
- [ ] Observability plan selected: logs, metrics, traces.
- [ ] Failure-mode tests listed.
- [ ] Secret management and JWT key rotation plan prepared.

## Assumptions and Defaults Chosen
- PostgreSQL is the default relational database for auth, ticket, workflow, rule, and NLG metadata.
- Transaction data uses sharded PostgreSQL/Citus, CockroachDB/YugabyteDB, or another horizontally scalable store depending on available infrastructure.
- Redis is used for rate limits, hot transaction cache, rule/template cache, and circuit-breaker state.
- Kafka is preferred for high-throughput event streaming; RabbitMQ is acceptable for simpler queue-based routing.
- Synchronous APIs return the safest available analysis quickly; non-critical audit, notification, and analytics work runs asynchronously.
- Strong consistency is required for auth, ticket creation, final decision records, and audit persistence.
- Eventual consistency is acceptable for department notifications, analytics, dashboards, and read replicas.
- Distributed transactions use Saga plus outbox rather than two-phase commit.
