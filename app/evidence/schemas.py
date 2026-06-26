from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas import TransactionInput


class EvidenceFeaturesRequest(BaseModel):
    ticket_id: str
    account_id: str | None = None
    transactions: list[TransactionInput] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")


class DuplicatePaymentFeature(BaseModel):
    transaction_id: str
    previous_transaction_id: str
    amount: float
    counterparty: str | None
    seconds_apart: float


class EvidenceFeaturesResponse(BaseModel):
    ticket_id: str
    account_id: str
    shard_id: int
    transaction_count: int
    transaction_ids: list[str]
    duplicate_payment: DuplicatePaymentFeature | None = None
    established_counterparties: list[str]
    latest_transaction_at: datetime | None = None
    cache_status: str


class TransactionLookupResponse(BaseModel):
    transaction: TransactionInput
    shard_id: int
    cache_status: str


class AccountTransactionsResponse(BaseModel):
    account_id: str
    shard_id: int
    transactions: list[TransactionInput]
    cache_status: str
