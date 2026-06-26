from __future__ import annotations

import hashlib
import time
from copy import deepcopy
from dataclasses import dataclass
from threading import RLock
from typing import Generic, TypeVar

from app.api.schemas import TransactionInput
from app.config import get_settings


class TransactionNotFoundError(Exception):
    pass


T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    expires_at: float


class InMemoryEvidenceRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._transactions_by_id: dict[str, TransactionInput] = {}
        self._account_index: dict[str, list[str]] = {}
        self._transaction_cache: dict[str, CacheEntry[TransactionInput]] = {}
        self._account_cache: dict[str, CacheEntry[list[TransactionInput]]] = {}

    def shard_for(self, key: str) -> int:
        settings = get_settings()
        shard_count = max(settings.evidence_shard_count, 1)
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % shard_count

    def upsert_transactions(self, account_id: str, transactions: list[TransactionInput]) -> None:
        with self._lock:
            ids = self._account_index.setdefault(account_id, [])
            seen = set(ids)
            for transaction in transactions:
                self._transactions_by_id[transaction.transaction_id] = transaction
                if transaction.transaction_id not in seen:
                    ids.append(transaction.transaction_id)
                    seen.add(transaction.transaction_id)
                self._transaction_cache.pop(transaction.transaction_id, None)
            self._account_cache.pop(account_id, None)

    def get_transaction(self, transaction_id: str) -> tuple[TransactionInput, str]:
        with self._lock:
            cached = self._get_cached(self._transaction_cache, transaction_id)
            if cached is not None:
                return deepcopy(cached), "hit"

            transaction = self._transactions_by_id.get(transaction_id)
            if transaction is None:
                raise TransactionNotFoundError(transaction_id)

            self._set_cached(self._transaction_cache, transaction_id, transaction)
            return deepcopy(transaction), "miss"

    def get_account_transactions(self, account_id: str) -> tuple[list[TransactionInput], str]:
        with self._lock:
            cached = self._get_cached(self._account_cache, account_id)
            if cached is not None:
                return deepcopy(cached), "hit"

            transaction_ids = self._account_index.get(account_id, [])
            transactions = [self._transactions_by_id[item] for item in transaction_ids if item in self._transactions_by_id]
            self._set_cached(self._account_cache, account_id, transactions)
            return deepcopy(transactions), "miss"

    def reset(self) -> None:
        with self._lock:
            self._transactions_by_id.clear()
            self._account_index.clear()
            self._transaction_cache.clear()
            self._account_cache.clear()

    def _get_cached(self, cache: dict[str, CacheEntry[T]], key: str) -> T | None:
        entry = cache.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            cache.pop(key, None)
            return None
        return entry.value

    def _set_cached(self, cache: dict[str, CacheEntry[T]], key: str, value: T) -> None:
        settings = get_settings()
        cache[key] = CacheEntry(value=deepcopy(value), expires_at=time.monotonic() + settings.evidence_cache_ttl_seconds)


evidence_repository = InMemoryEvidenceRepository()
