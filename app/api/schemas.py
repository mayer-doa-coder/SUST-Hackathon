from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.enums import (
    CaseType,
    Channel,
    Department,
    EvidenceVerdict,
    Language,
    Severity,
    TransactionStatus,
    TransactionType,
    UserType,
)


class TransactionInput(BaseModel):
    transaction_id: str
    timestamp: datetime
    type: TransactionType
    amount: float = Field(ge=0)
    counterparty: str | None = None
    status: TransactionStatus

    model_config = ConfigDict(extra="ignore")


class AnalyzeTicketRequest(BaseModel):
    ticket_id: str
    complaint: str
    language: Language | None = None
    channel: Channel | None = None
    user_type: UserType | None = UserType.UNKNOWN
    campaign_context: str | None = None
    transaction_history: list[TransactionInput] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None

    model_config = ConfigDict(extra="ignore")

    @field_validator("ticket_id")
    @classmethod
    def validate_ticket_id(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("ticket_id must be a string")
        if not value.strip():
            raise ValueError("ticket_id must not be empty")
        return value

    @field_validator("complaint")
    @classmethod
    def validate_complaint(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("complaint must be a string")
        if not value.strip():
            raise ValueError("complaint must not be empty")
        return value

    @model_validator(mode="before")
    @classmethod
    def normalize_null_transaction_history(cls, data: Any) -> Any:
        if isinstance(data, dict) and data.get("transaction_history") is None:
            data = dict(data)
            data["transaction_history"] = []
        return data


class AnalyzeTicketResponse(BaseModel):
    ticket_id: str
    relevant_transaction_id: str | None
    evidence_verdict: EvidenceVerdict
    case_type: CaseType
    severity: Severity
    department: Department
    agent_summary: str
    recommended_next_action: str
    customer_reply: str
    human_review_required: bool
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    reason_codes: list[str] | None = None

    model_config = ConfigDict(extra="ignore")


class ErrorBody(BaseModel):
    code: str
    message: str
    ticket_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody

