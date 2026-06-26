from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas import AnalyzeTicketRequest, TransactionInput
from app.domain.enums import CaseType, Department, EvidenceVerdict, Severity


class InvestigationEvaluateRequest(AnalyzeTicketRequest):
    account_id: str | None = None

    model_config = ConfigDict(extra="ignore")


class InvestigationDecisionResponse(BaseModel):
    ticket_id: str
    relevant_transaction_id: str | None
    evidence_verdict: EvidenceVerdict
    case_type: CaseType
    severity: Severity
    department: Department
    human_review_required: bool
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reason_codes: list[str]
    matched_transaction: TransactionInput | None = None
    language: str
    rule_version: str
    rules_cache_status: str


class ActiveRulesResponse(BaseModel):
    rule_version: str
    cache_status: str
    owner: str = "investigation-service"
    structured_fields: list[str]
    consistency_mode: str
