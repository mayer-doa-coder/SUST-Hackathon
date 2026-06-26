from __future__ import annotations

from app.config import get_settings
from app.core.llm import AnthropicNLGClient, NLGPayload
from app.core.nlg import build_template_summary
from app.core.reasoning import AnalysisFacts
from app.core.safety import enforce_customer_reply_safety
from app.domain.enums import Language, UserType
from app.nlg_service.schemas import NLGDecisionInput, NLGDraftRequest, NLGDraftResponse, SafetyValidateRequest, SafetyValidateResponse


class NLGAndSafetyService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.llm_client = AnthropicNLGClient(self.settings)

    async def draft(self, payload: NLGDraftRequest) -> NLGDraftResponse:
        facts = self._facts_from_decision(payload.decision)
        summary, next_action, customer_reply = build_template_summary(
            payload.ticket_id,
            payload.complaint,
            facts,
            payload.user_type,
        )
        fallback = NLGPayload(
            agent_summary=summary,
            recommended_next_action=next_action,
            customer_reply=customer_reply,
        )
        llm_payload = await self.llm_client.generate(payload.complaint, facts, fallback)
        safe_reply, replaced = enforce_customer_reply_safety(
            payload.ticket_id,
            payload.decision.language,
            payload.user_type,
            llm_payload.customer_reply,
        )
        used_fallback = llm_payload == fallback
        return NLGDraftResponse(
            agent_summary=llm_payload.agent_summary or summary,
            recommended_next_action=llm_payload.recommended_next_action or next_action,
            customer_reply=safe_reply,
            used_fallback=used_fallback,
            prompt_version=self.settings.nlg_prompt_version,
            template_version=self.settings.nlg_template_version,
            safety_policy_version=self.settings.safety_policy_version,
            safety_replaced=replaced,
            circuit_state=self._circuit_state(),
        )

    def validate_safety(self, payload: SafetyValidateRequest) -> SafetyValidateResponse:
        safe_reply, replaced = enforce_customer_reply_safety(
            payload.ticket_id,
            payload.language,
            payload.user_type,
            payload.customer_reply,
        )
        return SafetyValidateResponse(
            customer_reply=safe_reply,
            safe=not replaced,
            replaced=replaced,
            safety_policy_version=self.settings.safety_policy_version,
        )

    def _circuit_state(self) -> str:
        return "open" if self.llm_client.circuit_open_until is not None else "closed"

    def _facts_from_decision(self, decision: NLGDecisionInput) -> AnalysisFacts:
        return AnalysisFacts(
            relevant_transaction_id=decision.relevant_transaction_id,
            evidence_verdict=decision.evidence_verdict,
            case_type=decision.case_type,
            severity=decision.severity,
            department=decision.department,
            human_review_required=decision.human_review_required,
            confidence=decision.confidence,
            reason_codes=decision.reason_codes,
            matched_transaction=None,
            language=decision.language.value if isinstance(decision.language, Language) else str(decision.language),
        )


nlg_safety_service = NLGAndSafetyService()
