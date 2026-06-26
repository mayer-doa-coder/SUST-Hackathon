# QueueStorm Investigator Pre-Coding Execution Plan

## 1. Executive Summary

### Product Understanding
QueueStorm Investigator is an internal support copilot for a Bangladesh digital finance platform under campaign surge conditions. It is not a chatbot, not a generic classifier, and not a payment system. Its job is to investigate a complaint against the supplied transaction history, determine what the evidence supports, classify and route the case safely, and draft support-ready language.

### Business and User Reality
The business problem is operational collapse under campaign load: agents move from manageable queue volume to complaint saturation, and the cost of mistakes is unusually high because the domain is financial support. The direct user is the support agent. Secondary users are the receiving departments: dispute resolution, payments ops, merchant ops, agent ops, and fraud risk. Indirect users are customers and merchants who receive the drafted reply. Judges are also a practical user because machine-readable correctness determines scoreability.

### Requirement Priorities
Ground-truth, problem statement, rubric, and team manual all align on the same scoring truth:
- `GET /health` and `POST /analyze-ticket` must work first.
- Schema correctness is the gate to any score.
- Evidence reasoning is the highest-weight capability.
- Safety violations are catastrophic.
- Multilingual handling, especially Bangla numerals and Bangla replies, is mandatory.
- Deployment must be judgeable with no manual help.

### Architecture Understanding
The sound architectural center is a modular monolith with a deterministic rule engine for all scored structured fields and LLM usage limited to language understanding where needed plus NLG for the three text fields. The trust boundary is explicit:
- Rules own `relevant_transaction_id`, `evidence_verdict`, `case_type`, `severity`, `department`, `human_review_required`.
- LLM owns `agent_summary`, `recommended_next_action`, `customer_reply`.
- Safety enforcement is code after NLG, before response.

### Security and Safety Understanding
This is effectively a regulated communication system. Main controls:
- Never ask for PIN, OTP, password, or card number.
- Never promise refund, reversal, unblock, or recovery without authority.
- Never route customers to unofficial contacts.
- Never let complaint text override system behavior.
- Never leak secrets, stack traces, prompts, or internal details.

### AI Understanding
The docs consistently favor hybrid AI:
- Deterministic reasoning for evidence and routing.
- LLM for multilingual extraction only when rules are insufficient.
- LLM for human-quality summaries and customer replies.
- Template fallback when LLM is slow or unavailable.
- Circuit-breaker or equivalent fast failover is worth keeping because external API instability is a likely hackathon risk.

### Deployment and Evaluation Understanding
The highest-value deployment target is a single reachable HTTPS service with minimal moving parts. The team manual explicitly discourages heavyweight infra for this round. Evaluation is automated first, manual second, so the implementation order must be:
1. schema and endpoints
2. reasoning
3. safety
4. reliability/performance
5. docs and polish

### Key Constraints
- 4.5-hour hackathon window
- 30-second hard per-request timeout
- 60-second health readiness
- Docker image hard limit 1 GB from team manual
- No GPU, no huge local weights, no multi-GB downloads
- Stateless service
- Hidden tests include ambiguous, malformed, multilingual, and adversarial inputs

### Primary Risks
- Overbuilding infrastructure instead of scoring logic
- LLM latency causing timeout or instability
- Wrong transaction match on ambiguous inputs
- Unsafe reply text despite otherwise correct reasoning
- Bangla handling failing on numerals, time references, or reply language
- Schema drift from exact enum/type contract

---

## 2. Architecture Review

### Strengths in the HLD
- Correct core pattern: modular monolith, not microservices
- Correct trust boundary: rule engine for structured decisions, LLM for NLG
- Correct safety model: deterministic post-processing
- Correct fallback thinking: LLM fallback and template fallback
- Correct prioritization of statelessness, schema validation, and prompt-injection isolation
- Strong emphasis on ambiguity handling and `insufficient_data` over guessing

### Weaknesses / Unrealistic Assumptions
- HLD is materially overbuilt for a 4.5-hour preliminary round.
- Redis, PostgreSQL, Kafka, NGINX, Prometheus, Grafana, OpenTelemetry, Jaeger, blue-green deploys, HPA, and Kubernetes are not scoring-critical and create integration risk.
- Health checks that depend on Redis/Postgres conflict with the hackathon need for fast readiness and minimal failure surface.
- Production-grade observability and replication design are architecturally fine but hackathon-negative.
- CQRS/outbox/eventing are unjustified for a two-endpoint stateless service with no real integration consumers.
- Idempotency via Redis is useful in theory but not on the must-have path for preliminary scoring.

### Underengineering Risks in the HLD
- The HLD underplays the cost of Bangla time interpretation and timezone alignment in a pure rule path.
- It also leaves some open product decisions unresolved, especially reason code taxonomy and exact high-value threshold.

### Bottlenecks
- External LLM latency and rate limits
- Transaction matching ambiguity
- Bangla and mixed-language extraction
- Safety validation coverage
- Cold-start and deployment stability if extra infra is added

### Recommended Improvements While Preserving Architecture
- Preserve the modular monolith and rule/LLM separation exactly.
- Simplify deployment to a single FastAPI/Uvicorn service in one container.
- Replace Redis/Postgres/Kafka/NGINX/observability stack with in-process logging and optional in-memory resilience mechanisms.
- Keep template fallback and a lightweight circuit-breaker.
- Make `/health` independent of optional downstreams.
- Treat audit persistence, distributed rate limiting, and deep observability as postponed.
- Keep response generation deterministic enough that the service remains useful even with no LLM key.

### What to Implement Now / Mock / Simplify / Postpone
Implement now:
- API contract
- validation
- rule engine
- safety layer
- template fallback
- optional primary LLM integration
- Docker and deployment
Mock or simplify:
- LLM provider failover can be one primary provider plus templates if time is tight
- confidence and reason_codes can be simple deterministic additions
Postpone:
- Redis
- PostgreSQL
- NGINX
- Kubernetes
- Kafka/outbox
- Prometheus/Grafana/OTel
- blue-green rollout
- replicated infra
- advanced caching and distributed idempotency

---

## 3. Evaluation Strategy

### Highest-Scoring Items
- Evidence Reasoning `35%`
- Safety & Escalation `20%`
- API Contract & Schema `15%`

### Mandatory Items
- Exact endpoints
- Exact required response fields and enums
- Controlled malformed-input handling
- Safe customer replies
- Correct fraud escalation
- Bangla complaint support
- Reachable deployment or runnable Docker fallback

### Nice-to-Have Items
- `confidence`
- `reason_codes`
- polished multilingual tone
- formal merchant tone
- fallback/circuit-breaker sophistication
- cost-aware model selection explanation in README

### Common Failure Points
- Wrong enum spelling or boolean type
- Guessing a transaction when evidence is ambiguous
- Using LLM to decide structured fields
- Unsafe phrases like “we will refund you”
- English-only replies
- deployment not reachable
- health endpoint tied to non-essential dependencies

### Hidden Scoring Opportunities
- Strong `insufficient_data` behavior
- Established recipient inconsistency detection
- Correct duplicate-payment selection of the second transaction
- Bangla numeral normalization
- Merchant tone differentiation
- Honest, limited, safe fallback replies when data is unclear

### Engineering Focus Order
1. schema and endpoint correctness
2. transaction matching and evidence verdict
3. safety guardrails
4. multilingual correctness
5. LLM polish and fallback quality
6. deployment reproducibility
7. documentation and submission quality

---

## 4. Implementation Roadmap

### Milestone 1: Service Skeleton and Contract Gate
- Goal: runnable API with `GET /health`, request/response schemas, global error handling
- Why: unlocks judge reachability and prevents unscoreable outputs
- Business value: makes the service externally testable immediately
- Components: app bootstrap, routing, schema definitions, enum source of truth, error mapper, config loading
- Files involved: app entrypoint, API schemas, enums/constants, config, error handlers
- Dependencies: none
- Deliverables: health endpoint, analyze route stub, 400/422/500 contract shape
- Testing strategy: curl/manual contract tests; malformed JSON; missing fields; empty complaint; unknown fields
- Acceptance criteria: `/health` returns `{"status":"ok"}`; `/analyze-ticket` returns controlled schema-valid responses and never crashes
- Risks: schema drift, wrong status codes
- Mitigation: central enum/constants and response-model validation
- Estimated time: 25 minutes

### Milestone 2: Deterministic Input Normalization and Parsing
- Goal: normalize complaints and prepare structured complaint signals without LLM dependence for English and partial multilingual support
- Why: matching accuracy starts with clean extraction
- Business value: reduces false routing and improves hidden-test robustness
- Components: language detection, Bangla numeral normalization, complaint sanitization, basic extraction of amount/time/type/counterparty/fraud cues
- Files involved: language detector, input normalizer, intent extractor, constants for keywords/patterns
- Dependencies: milestone 1
- Deliverables: normalized complaint context object for downstream rule engine
- Testing strategy: sample-driven tests for English, Bangla numerals, Banglish, vague complaints, fraud keywords
- Acceptance criteria: extracted values feed rule engine consistently; complaint language inferred when missing; Bangla numerals parsed
- Risks: brittle Bangla parsing
- Mitigation: use minimal rules plus optional LLM assist later for Bangla/mixed only
- Estimated time: 30 minutes

### Milestone 3: Core Investigation Rule Engine
- Goal: produce correct structured decision fields without any LLM requirement
- Why: this is the main scoring engine
- Business value: maximizes evidence reasoning score and ensures reliable routing
- Components: transaction matcher, duplicate detector, established-recipient check, evidence verdict, classifier, severity mapping, department router, human review engine, optional confidence/reason codes
- Files involved: matcher, verdict engine, classifier, severity/department/human review tables, confidence/reasoning helpers
- Dependencies: milestone 2
- Deliverables: full structured response except polished text fields
- Testing strategy: all 10 public cases plus adversarial unit cases for ambiguity, no-match, wrong day, pending, duplicate, phishing
- Acceptance criteria: public sample structured fields are functionally equivalent; ambiguous cases return `null` + `insufficient_data`; phishing always overrides
- Risks: wrong precedence, overmatching, timezone mismatches
- Mitigation: strict ordered rules from ground-truth; prefer `insufficient_data` over guess; assume BST complaint references against UTC timestamps
- Estimated time: 70 minutes

### Milestone 4: Safety Layer and Safe Template NLG
- Goal: guarantee safe text outputs even without external AI
- Why: safety penalties can erase an otherwise strong score
- Business value: protects final score and keeps service usable during LLM outage
- Components: safe English/Bangla templates, merchant-tone variants, post-generation safety scanner, reply replacement policy
- Files involved: fallback NLG, safety enforcer, prompt/output safety constants
- Dependencies: milestone 3
- Deliverables: deterministic `agent_summary`, `recommended_next_action`, `customer_reply` generation path and safety gate
- Testing strategy: injection complaint tests, OTP-asking test, unauthorized refund wording test, suspicious contact test
- Acceptance criteria: unsafe outputs are replaced; no reply asks for credentials or promises outcomes; public cases remain functionally safe
- Risks: regex misses unsafe phrasing
- Mitigation: combine keyword patterns with small allow/deny phrase lists derived from sample pack and docs
- Estimated time: 25 minutes

### Milestone 5: LLM-Assisted NLG and Multilingual Upgrade
- Goal: improve quality of summaries/replies and handle Bangla/mixed extraction gaps without risking structured correctness
- Why: supports manual-review score and multilingual edge cases
- Business value: better agent usability and customer-facing tone
- Components: one primary LLM client, optional secondary fallback if time permits, structured NLG prompt, optional Bangla/mixed extraction assist, circuit-breaker or fast failure counter, template fallback path
- Files involved: LLM client, prompt builder, circuit breaker, NLG orchestrator
- Dependencies: milestones 3-4
- Deliverables: production path where rules compute facts and LLM only verbalizes them
- Testing strategy: run sample pack with and without LLM keys; verify English agent summary; Bangla customer reply; safe fallback when LLM unavailable
- Acceptance criteria: service remains correct without LLM; with LLM, replies improve but structured fields never change ownership
- Risks: timeout, rate limit, malformed LLM JSON
- Mitigation: hard timeout, narrow output contract, immediate template fallback, never trust LLM on transaction ID or routing
- Estimated time: 40 minutes

### Milestone 6: End-to-End Hardening and Deployment
- Goal: make the service judgeable, reproducible, and stable
- Why: a correct local service that is unreachable scores poorly
- Business value: converts implementation into a valid submission
- Components: Dockerfile, env handling, external deployment, sample output artifact, README/runbook
- Files involved: Dockerfile, dependency file, README, `.env.example`, sample output, optional runbook
- Dependencies: milestones 1-5
- Deliverables: public endpoint or Docker fallback, complete documentation
- Testing strategy: cold start health test, all sample cases against deployed instance, malformed input smoke tests, image-size check
- Acceptance criteria: public `/health` and `/analyze-ticket` reachable; startup <60s; image <1GB; README complete
- Risks: deployment instability, oversized image, secret leakage
- Mitigation: slim base image, env vars only, no heavyweight infra, final repository secret sweep
- Estimated time: 35 minutes

### Milestone 7: Submission Lock and Final Verification
- Goal: freeze a clean, runnable, high-scoring submission
- Why: final minutes should reduce risk, not add features
- Business value: preserves working state before deadline
- Components: final test matrix, submission form completion, fallback readiness
- Files involved: none new beyond docs/submission artifacts
- Dependencies: milestone 6
- Deliverables: validated endpoint, submission answers, final sample output, checklist signoff
- Testing strategy: re-run core samples, safety prompts, one Bangla case, one malformed request, one no-history case
- Acceptance criteria: no blocking regressions; all must-have checks pass
- Risks: late-stage breakage from “one more improvement”
- Mitigation: code freeze after verification, only blocker fixes
- Estimated time: 15 minutes

---

## 5. Dependency Graph

```text
Milestone 1: Service Skeleton
        |
        v
Milestone 2: Normalization and Parsing
        |
        v
Milestone 3: Core Investigation Rule Engine
        |
        +----------------------+
        |                      |
        v                      v
Milestone 4: Safety +         Milestone 5: LLM NLG Upgrade
Template Fallback              |
        |                      |
        +----------+-----------+
                   |
                   v
        Milestone 6: Deployment and Docs
                   |
                   v
        Milestone 7: Submission Lock
```

Critical logic dependency graph:

```text
Schema/Enums
  |
  v
Input Validation
  |
  v
Normalization + Language Detection
  |
  v
Intent Extraction
  |
  v
Transaction Matching
  |
  v
Evidence Verdict
  |
  v
Case Classification
  |
  v
Severity + Department + Human Review
  |
  +--> Template Text
  |
  +--> LLM NLG
          |
          v
     Safety Enforcement
          |
          v
   Response Validation
          |
          v
      Deployment
```

---

## 6. Critical Path

### MUST HAVE
- Milestones 1, 2, 3, 4, 6, 7
- Why: they cover scoreability, core evidence score, safety score, and deployment score

### SHOULD HAVE
- Milestone 5 with at least one primary LLM and template fallback
- Why: helps Bangla/mixed nuance and manual response-quality review, but service must remain competitive without it

### NICE TO HAVE
- secondary LLM provider
- confidence and richer reason_codes
- lightweight request correlation logging
- idempotency cache
- formal merchant tone tuning beyond baseline
- Why: useful but not worth risking core path

### Hackathon Simplification Decisions
Implement now:
- one container
- one API process
- deterministic tables/rules
- template fallback
Simplify:
- `/health` checks only app readiness
- logging to stdout JSON or plain structured logs
- in-process circuit-breaker state
Postpone:
- Redis, Postgres, Kafka, NGINX, k8s, observability stack, distributed rate limits

---

## 7. Engineering Task Breakdown

### Engineer A: API / Platform / Deployment Lead
- Build app skeleton, schemas, enums, error handling, config
- Own `/health`, `/analyze-ticket`, output validation
- Own Dockerfile, deployment, README/runbook, `.env.example`
- Merge points: after milestone 1 for route integration, after milestone 6 for deployment freeze

### Engineer B: Investigation Logic Lead
- Build normalization, extraction, transaction matcher, evidence verdict
- Build classifier, severity, department, human review, confidence/reason codes
- Own sample-case parity for structured fields
- Merge points: integrates into route after milestone 3

### Engineer C: AI / Safety / QA Lead
- Build safety enforcer and template fallback first
- Then add LLM client, prompt builder, fallback orchestration, merchant/Bangla tone handling
- Own adversarial tests, Bangla checks, public sample verification harness
- Merge points: safety joins after milestone 4, LLM joins after milestone 5

### Parallelization Plan
- A and B start immediately after document alignment.
- C starts with safety templates and test harness while B builds rules.
- A integrates B’s structured engine first, then C’s safety layer, then C’s LLM path.
- Final integration order: contract -> rules -> safety -> LLM -> deployment.

---

## 8. Hackathon Time Allocation

- 0:00-0:20 setup, schema, skeleton, role split
- 0:20-0:50 normalization and validation hardening
- 0:50-2:00 core rule engine and public sample parity
- 2:00-2:25 safety layer and template fallback
- 2:25-3:05 LLM integration only if core path is stable
- 3:05-3:40 Docker, deployment, external smoke tests
- 3:40-4:10 README, sample output, runbook, submission text
- 4:10-4:30 freeze, re-test, submit

Time-budget rule:
- If milestone 3 slips, milestone 5 is reduced before milestone 4 or 6 are reduced.
- If deployment slips, fallback to Docker path immediately rather than spending late time on infra debugging.

---

## 9. Agent Mode Prompt Sequence

### Milestone 1 Prompt
“Read `CLAUDE.md`, then re-read `docs/ground-truth.md`, `docs/QueueStorm_Problem_Analysis.md`, `docs/QueueStorm_Investigator_PRD.md`, and `docs/QueueStorm_Investigator_HLD.md` before changing anything. Implement only the minimum runnable service skeleton for QueueStorm Investigator: exact `GET /health`, exact route for `POST /analyze-ticket`, centralized enums/constants, request/response schemas, config loading, and controlled error handling. Keep the project runnable at all times, follow the HLD modular-monolith direction, avoid architectural drift, and stop to ask if any assumption is required.”

### Milestone 2 Prompt
“Read `CLAUDE.md` and re-read the project source-of-truth docs, especially `ground-truth.md` and the API contract sections. Implement input validation and normalization only: malformed JSON handling, missing/invalid field handling, empty complaint handling, `transaction_history: null` coercion, extra-field ignore behavior, language hint handling, and Bangla numeral normalization. Do not break existing endpoints. Keep the service runnable and schema-exact.”

### Milestone 3 Prompt
“Read `CLAUDE.md`, `ground-truth.md`, the transaction-matching and classification rules in the PRD/HLD, and the public sample cases before editing. Implement the deterministic investigation core only: complaint signal extraction, transaction matching, evidence verdict, duplicate-payment detection, established-recipient inconsistency detection, case classification, severity, department routing, human review, and optional confidence/reason codes. All structured decisions must remain rule-owned, never LLM-owned. Preserve runnability and stop if assumptions are needed.”

### Milestone 4 Prompt
“Read `CLAUDE.md`, `ground-truth.md`, and the safety sections of the Problem Statement, PRD, and HLD before making changes. Implement the deterministic safety layer and template fallback text generation. Enforce all safety rules after text generation, replace unsafe customer-facing text with safe templates, and ensure no previous milestone behavior regresses. Keep the project runnable and avoid architectural drift.”

### Milestone 5 Prompt
“Read `CLAUDE.md`, `ground-truth.md`, and the AI architecture sections again before editing. Implement LLM-backed NLG only within the approved trust boundary: rules continue to own all structured fields, and the LLM may generate only `agent_summary`, `recommended_next_action`, and `customer_reply`, plus optional multilingual extraction support where rules are insufficient. Add strict prompt isolation, timeouts, and template fallback. Keep the project runnable and stop if any assumption is required.”

### Milestone 6 Prompt
“Read `CLAUDE.md`, `ground-truth.md`, deployment requirements, the team manual, and rubric before making changes. Implement only the deployment and reproducibility layer needed for hackathon judging: Dockerfile, environment variable wiring, startup command, and documentation artifacts. Do not introduce heavyweight infrastructure that increases risk. Preserve all previous milestone behavior and keep the service externally runnable.”

### Milestone 7 Prompt
“Read `CLAUDE.md`, `ground-truth.md`, the rubric, and sample cases before any final edits. Perform final hardening only: fix blocking regressions, verify sample-case parity, verify safety behavior, verify malformed-input handling, and prepare the repository for submission without architectural drift. Do not add speculative features. Keep the project runnable, and stop to ask before making any non-trivial behavioral change.”

---

## 10. Risk Matrix

| Risk | Likelihood | Impact | Mitigation |
|---|---|---:|---|
| Schema mismatch | Medium | High | Central enums, response-model validation, early sample-case tests |
| Ambiguous transaction misclassified as clear match | Medium | High | Prefer `insufficient_data`, explicit ambiguity thresholds |
| Unsafe reply text | Medium | Critical | Deterministic post-NLG safety gate with replacement templates |
| LLM timeout/rate limit | High | Medium | Template fallback, hard timeouts, minimal provider dependence |
| Bangla extraction weakness | Medium | High | Bangla numeral normalization first, LLM assist only for complex multilingual cases |
| Overengineered infra slows delivery | High | High | Single-service deployment only, postpone Redis/DB/k8s |
| Health endpoint blocked by optional dependencies | Medium | High | App-only health readiness |
| Late deployment failure | Medium | High | Choose simplest hosting path, keep Docker fallback ready |
| Hidden prompt injection case | High | High | prompt isolation + output safety enforcement |
| Merchant-tone/manual-review polish underdeveloped | Medium | Medium | Add explicit merchant templates and formal reply style |

---

## 11. Pre-Coding Checklist

- [ ] `CLAUDE.md` read completely
- [ ] Documentation read in required priority order
- [ ] Ground-truth conflicts resolved in favor of `ground-truth.md`
- [ ] Exact API schema and enum values locked
- [ ] Public sample cases analyzed for reasoning patterns
- [ ] Evaluation rubric translated into build priority
- [ ] Safety rules translated into deterministic checks
- [ ] Rule engine ownership boundary agreed
- [ ] LLM trust boundary agreed
- [ ] Bangla numeral and language-handling strategy agreed
- [ ] Heavy infra explicitly deferred for preliminary round
- [ ] Deployment target selected
- [ ] Docker fallback path selected
- [ ] Environment variable list prepared
- [ ] Milestone owners assigned across 3 engineers
- [ ] Freeze rule agreed: no speculative features after deployment starts

## Assumptions and Defaults Chosen
- High-value threshold for mandatory human review: use `>= 10,000 BDT` from `ground-truth.md`.
- Complaint-local time references are interpreted in Bangladesh Standard Time and compared against UTC transaction timestamps.
- `reason_codes` remain optional and may use concise descriptive strings rather than a rigid taxonomy.
- `confidence` is optional and deterministic; omit rather than guess if implementation time is constrained.
- Health check returns application readiness and does not fail because optional infra is absent.
- Production-grade components named in the HLD are preserved as future architecture, not preliminary-round scope.
