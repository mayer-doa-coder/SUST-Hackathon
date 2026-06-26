from __future__ import annotations

from fastapi import APIRouter

from app.evidence.schemas import AccountTransactionsResponse, EvidenceFeaturesRequest, EvidenceFeaturesResponse, TransactionLookupResponse
from app.evidence.service import transaction_evidence_service


router = APIRouter(tags=["transaction-evidence"])


@router.get("/transactions/{transaction_id}", response_model=TransactionLookupResponse)
async def get_transaction(transaction_id: str) -> TransactionLookupResponse:
    return transaction_evidence_service.get_transaction(transaction_id)


@router.get("/accounts/{account_id}/transactions", response_model=AccountTransactionsResponse)
async def get_account_transactions(account_id: str) -> AccountTransactionsResponse:
    return transaction_evidence_service.get_account_transactions(account_id)


@router.post("/evidence/features", response_model=EvidenceFeaturesResponse)
async def build_evidence_features(payload: EvidenceFeaturesRequest) -> EvidenceFeaturesResponse:
    return transaction_evidence_service.prepare_features(payload.ticket_id, payload.transactions, payload.account_id)
