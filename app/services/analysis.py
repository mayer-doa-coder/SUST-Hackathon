from __future__ import annotations

from app.api.schemas import AnalyzeTicketRequest, AnalyzeTicketResponse
from app.config import get_settings
from app.core.normalization import sanitize_complaint
from app.domain.enums import UserType
from app.evidence.service import transaction_evidence_service
from app.investigation.service import investigation_service
from app.nlg_service.schemas import NLGDecisionInput, NLGDraftRequest
from app.nlg_service.service import nlg_safety_service


settings = get_settings()


async def analyze_ticket(payload: AnalyzeTicketRequest) -> AnalyzeTicketResponse:
    user_type = payload.user_type or UserType.UNKNOWN
    sanitized_complaint = sanitize_complaint(payload.complaint, settings.llm_max_complaint_chars)
    evidence_features = transaction_evidence_service.prepare_features(payload.ticket_id, payload.transaction_history)
    facts, rule_version, rules_cache_status = investigation_service.evaluate(payload, sanitized_complaint)
    draft = await nlg_safety_service.draft(
        NLGDraftRequest(
            ticket_id=payload.ticket_id,
            complaint=sanitized_complaint,
            user_type=user_type,
            decision=NLGDecisionInput(
                relevant_transaction_id=facts.relevant_transaction_id,
                evidence_verdict=facts.evidence_verdict,
                case_type=facts.case_type,
                severity=facts.severity,
                department=facts.department,
                human_review_required=facts.human_review_required,
                confidence=facts.confidence,
                reason_codes=facts.reason_codes,
                language=facts.language,
            ),
        )
    )

    reason_codes = list(facts.reason_codes)
    reason_codes.append(f"evidence_shard_{evidence_features.shard_id}")
    reason_codes.append(f"ruleset_{rule_version}")
    if rules_cache_status == "hit":
        reason_codes.append("rules_cache_hit")
    if evidence_features.duplicate_payment is not None and "duplicate_payment_candidate" not in reason_codes:
        reason_codes.append("duplicate_payment_candidate")
    reason_codes.append(f"nlg_template_{draft.template_version}")
    reason_codes.append(f"safety_policy_{draft.safety_policy_version}")
    if draft.used_fallback:
        reason_codes.append("nlg_template_fallback")
    if draft.safety_replaced:
        reason_codes.append("safety_replaced")

    return AnalyzeTicketResponse(
        ticket_id=payload.ticket_id,
        relevant_transaction_id=facts.relevant_transaction_id,
        evidence_verdict=facts.evidence_verdict,
        case_type=facts.case_type,
        severity=facts.severity,
        department=facts.department,
        agent_summary=draft.agent_summary,
        recommended_next_action=draft.recommended_next_action,
        customer_reply=draft.customer_reply,
        human_review_required=facts.human_review_required,
        confidence=facts.confidence,
        reason_codes=reason_codes or None,
    )
