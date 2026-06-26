from __future__ import annotations

from app.api.schemas import AnalyzeTicketRequest
from app.core.intent import extract_intent
from app.core.language import detect_language
from app.core.normalization import sanitize_complaint
from app.core.reasoning import AnalysisFacts, investigate
from app.config import get_settings
from app.domain.enums import UserType
from app.investigation.rules import rule_config_repository
from app.investigation.schemas import ActiveRulesResponse, InvestigationDecisionResponse


class InvestigationService:
    def evaluate(
        self,
        payload: AnalyzeTicketRequest,
        sanitized_complaint: str | None = None,
    ) -> tuple[AnalysisFacts, str, str]:
        settings = get_settings()
        ruleset, cache_status = rule_config_repository.active_ruleset()
        user_type = payload.user_type or UserType.UNKNOWN
        complaint = sanitized_complaint or sanitize_complaint(payload.complaint, settings.llm_max_complaint_chars)
        language = detect_language(complaint, payload.language)
        transaction_timestamps = [transaction.timestamp for transaction in payload.transaction_history]
        intent = extract_intent(complaint, language, transaction_timestamps)
        facts = investigate(intent, payload.transaction_history, user_type)
        return facts, ruleset.version, cache_status

    def evaluate_response(
        self,
        payload: AnalyzeTicketRequest,
        sanitized_complaint: str | None = None,
    ) -> InvestigationDecisionResponse:
        facts, rule_version, cache_status = self.evaluate(payload, sanitized_complaint)
        return self.to_response(payload.ticket_id, facts, rule_version, cache_status)

    def active_rules(self) -> ActiveRulesResponse:
        ruleset, cache_status = rule_config_repository.active_ruleset()
        return ActiveRulesResponse(
            rule_version=ruleset.version,
            cache_status=cache_status,
            structured_fields=list(ruleset.structured_fields),
            consistency_mode=ruleset.consistency_mode,
        )

    def to_response(
        self,
        ticket_id: str,
        facts: AnalysisFacts,
        rule_version: str,
        cache_status: str,
    ) -> InvestigationDecisionResponse:
        return InvestigationDecisionResponse(
            ticket_id=ticket_id,
            relevant_transaction_id=facts.relevant_transaction_id,
            evidence_verdict=facts.evidence_verdict,
            case_type=facts.case_type,
            severity=facts.severity,
            department=facts.department,
            human_review_required=facts.human_review_required,
            confidence=facts.confidence,
            reason_codes=facts.reason_codes,
            matched_transaction=facts.matched_transaction,
            language=facts.language,
            rule_version=rule_version,
            rules_cache_status=cache_status,
        )


investigation_service = InvestigationService()
