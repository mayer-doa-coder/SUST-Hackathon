from __future__ import annotations

import time
from dataclasses import dataclass
from threading import RLock

from app.config import get_settings


@dataclass(frozen=True)
class RuleSet:
    version: str
    structured_fields: tuple[str, ...]
    consistency_mode: str


@dataclass
class _RuleCacheEntry:
    ruleset: RuleSet
    expires_at: float


class RuleConfigRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._cached: _RuleCacheEntry | None = None

    def active_ruleset(self) -> tuple[RuleSet, str]:
        settings = get_settings()
        now = time.monotonic()
        with self._lock:
            if self._cached is not None and self._cached.expires_at > now:
                return self._cached.ruleset, "hit"

            ruleset = RuleSet(
                version=settings.investigation_active_ruleset_version,
                structured_fields=(
                    "relevant_transaction_id",
                    "evidence_verdict",
                    "case_type",
                    "severity",
                    "department",
                    "human_review_required",
                ),
                consistency_mode="strong active-rule version read, last-known-good fallback",
            )
            self._cached = _RuleCacheEntry(
                ruleset=ruleset,
                expires_at=now + settings.investigation_rule_cache_ttl_seconds,
            )
            return ruleset, "miss"

    def reset(self) -> None:
        with self._lock:
            self._cached = None


rule_config_repository = RuleConfigRepository()
