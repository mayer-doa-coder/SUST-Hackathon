from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import CaseType, Department, EvidenceVerdict, Language, Severity, TransactionStatus, TransactionType, UserType


class NLGDecisionInput(BaseModel):
    relevant_transaction_id: str | None = None
    evidence_verdict: EvidenceVerdict
    case_type: CaseType
    severity: Severity
    department: Department
    human_review_required: bool
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    language: Language = Language.EN
    matched_transaction_id: str | None = None
    matched_transaction_type: TransactionType | None = None
    matched_transaction_amount: float | None = None
    matched_transaction_status: TransactionStatus | None = None


class NLGDraftRequest(BaseModel):
    ticket_id: str
    complaint: str
    user_type: UserType = UserType.UNKNOWN
    decision: NLGDecisionInput

    model_config = ConfigDict(extra="ignore")


class NLGDraftResponse(BaseModel):
    agent_summary: str
    recommended_next_action: str
    customer_reply: str
    used_fallback: bool
    prompt_version: str
    template_version: str
    safety_policy_version: str
    safety_replaced: bool
    circuit_state: str


class SafetyValidateRequest(BaseModel):
    ticket_id: str
    customer_reply: str
    language: Language = Language.EN
    user_type: UserType = UserType.UNKNOWN

    model_config = ConfigDict(extra="ignore")


class SafetyValidateResponse(BaseModel):
    customer_reply: str
    safe: bool
    replaced: bool
    safety_policy_version: str
