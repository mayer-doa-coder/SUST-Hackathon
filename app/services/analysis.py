from __future__ import annotations

from app.api.schemas import AnalyzeTicketRequest, AnalyzeTicketResponse
from app.config import get_settings
from app.core.intent import extract_intent
from app.core.language import detect_language
from app.core.llm import AnthropicNLGClient, NLGPayload
from app.core.nlg import build_template_summary
from app.core.normalization import sanitize_complaint
from app.core.reasoning import investigate
from app.core.safety import enforce_customer_reply_safety
from app.domain.enums import UserType


settings = get_settings()
llm_client = AnthropicNLGClient(settings)


async def analyze_ticket(payload: AnalyzeTicketRequest) -> AnalyzeTicketResponse:
    user_type = payload.user_type or UserType.UNKNOWN
    sanitized_complaint = sanitize_complaint(payload.complaint, settings.llm_max_complaint_chars)
    language = detect_language(sanitized_complaint, payload.language)
    transaction_timestamps = [txn.timestamp for txn in payload.transaction_history]
    intent = extract_intent(sanitized_complaint, language, transaction_timestamps)
    facts = investigate(intent, payload.transaction_history, user_type)

    summary, next_action, customer_reply = build_template_summary(
        payload.ticket_id,
        sanitized_complaint,
        facts,
        user_type,
    )

    llm_payload = await llm_client.generate(
        sanitized_complaint,
        facts,
        NLGPayload(
            agent_summary=summary,
            recommended_next_action=next_action,
            customer_reply=customer_reply,
        ),
    )

    safe_reply, violated = enforce_customer_reply_safety(
        payload.ticket_id,
        language,
        user_type,
        llm_payload.customer_reply,
    )

    reason_codes = list(facts.reason_codes)
    if violated:
        reason_codes.append("safety_replaced")

    return AnalyzeTicketResponse(
        ticket_id=payload.ticket_id,
        relevant_transaction_id=facts.relevant_transaction_id,
        evidence_verdict=facts.evidence_verdict,
        case_type=facts.case_type,
        severity=facts.severity,
        department=facts.department,
        agent_summary=llm_payload.agent_summary or summary,
        recommended_next_action=llm_payload.recommended_next_action or next_action,
        customer_reply=safe_reply,
        human_review_required=facts.human_review_required,
        confidence=facts.confidence,
        reason_codes=reason_codes or None,
    )
