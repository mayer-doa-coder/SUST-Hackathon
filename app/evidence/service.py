from __future__ import annotations

from collections import Counter

from app.api.schemas import TransactionInput
from app.domain.enums import TransactionStatus, TransactionType
from app.evidence.repository import evidence_repository
from app.evidence.schemas import (
    AccountTransactionsResponse,
    DuplicatePaymentFeature,
    EvidenceFeaturesResponse,
    TransactionLookupResponse,
)


def _account_id(ticket_id: str, account_id: str | None) -> str:
    return account_id or f"ticket:{ticket_id}"


class TransactionEvidenceService:
    def prepare_features(
        self,
        ticket_id: str,
        transactions: list[TransactionInput],
        account_id: str | None = None,
    ) -> EvidenceFeaturesResponse:
        resolved_account_id = _account_id(ticket_id, account_id)
        evidence_repository.upsert_transactions(resolved_account_id, transactions)
        account_transactions, cache_status = evidence_repository.get_account_transactions(resolved_account_id)

        return EvidenceFeaturesResponse(
            ticket_id=ticket_id,
            account_id=resolved_account_id,
            shard_id=evidence_repository.shard_for(resolved_account_id),
            transaction_count=len(account_transactions),
            transaction_ids=[transaction.transaction_id for transaction in account_transactions],
            duplicate_payment=self._find_duplicate_payment(account_transactions),
            established_counterparties=self._established_counterparties(account_transactions),
            latest_transaction_at=max((transaction.timestamp for transaction in account_transactions), default=None),
            cache_status=cache_status,
        )

    def get_transaction(self, transaction_id: str) -> TransactionLookupResponse:
        transaction, cache_status = evidence_repository.get_transaction(transaction_id)
        return TransactionLookupResponse(
            transaction=transaction,
            shard_id=evidence_repository.shard_for(transaction.transaction_id),
            cache_status=cache_status,
        )

    def get_account_transactions(self, account_id: str) -> AccountTransactionsResponse:
        transactions, cache_status = evidence_repository.get_account_transactions(account_id)
        return AccountTransactionsResponse(
            account_id=account_id,
            shard_id=evidence_repository.shard_for(account_id),
            transactions=transactions,
            cache_status=cache_status,
        )

    def _find_duplicate_payment(self, transactions: list[TransactionInput]) -> DuplicatePaymentFeature | None:
        sorted_transactions = sorted(transactions, key=lambda item: item.timestamp)
        for index in range(1, len(sorted_transactions)):
            previous = sorted_transactions[index - 1]
            current = sorted_transactions[index]
            seconds_apart = (current.timestamp - previous.timestamp).total_seconds()
            if (
                previous.type == TransactionType.PAYMENT
                and current.type == TransactionType.PAYMENT
                and previous.amount == current.amount
                and previous.counterparty == current.counterparty
                and previous.status == TransactionStatus.COMPLETED
                and current.status == TransactionStatus.COMPLETED
                and seconds_apart <= 60
            ):
                return DuplicatePaymentFeature(
                    transaction_id=current.transaction_id,
                    previous_transaction_id=previous.transaction_id,
                    amount=current.amount,
                    counterparty=current.counterparty,
                    seconds_apart=seconds_apart,
                )
        return None

    def _established_counterparties(self, transactions: list[TransactionInput]) -> list[str]:
        transfer_counterparties = [
            transaction.counterparty
            for transaction in transactions
            if transaction.type == TransactionType.TRANSFER and transaction.counterparty
        ]
        counts = Counter(transfer_counterparties)
        return sorted(counterparty for counterparty, count in counts.items() if count >= 2)


transaction_evidence_service = TransactionEvidenceService()
