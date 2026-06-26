from __future__ import annotations

import hashlib

from app.config import get_settings
from app.platform.schemas import (
    CachePolicy,
    DatabaseRouteResponse,
    DatabaseScalingPlan,
    LoadTestPlan,
    ScalingPlanResponse,
    ServiceReplicaPlan,
    ShardRoutingPlan,
)


class PlatformScalingService:
    def scaling_plan(self) -> ScalingPlanResponse:
        settings = get_settings()
        read_replicas = self._read_replicas()
        return ScalingPlanResponse(
            load_balancer="external L7 load balancer -> API gateway replicas; internal service load balancing by service name",
            service_replicas=[
                ServiceReplicaPlan(service="api-gateway", replicas=settings.gateway_replica_count, load_balancer_scope="external"),
                ServiceReplicaPlan(service="auth", replicas=settings.auth_replica_count, load_balancer_scope="internal"),
                ServiceReplicaPlan(service="ticket-intake", replicas=settings.ticket_replica_count, load_balancer_scope="internal"),
                ServiceReplicaPlan(service="transaction-evidence", replicas=settings.evidence_replica_count, load_balancer_scope="internal"),
                ServiceReplicaPlan(service="investigation", replicas=settings.investigation_replica_count, load_balancer_scope="internal"),
                ServiceReplicaPlan(service="nlg-safety", replicas=settings.nlg_replica_count, load_balancer_scope="internal"),
                ServiceReplicaPlan(service="case-orchestration", replicas=settings.workflow_replica_count, load_balancer_scope="internal"),
                ServiceReplicaPlan(service="pubsub-audit-routing", replicas=settings.messaging_replica_count, load_balancer_scope="internal"),
            ],
            database_scaling=[
                self._db_plan("auth", read_replicas),
                self._db_plan("ticket-intake", read_replicas),
                self._db_plan("workflow", read_replicas),
                self._db_plan("rules", read_replicas),
                self._db_plan("nlg-safety", read_replicas),
            ],
            shard_routing=ShardRoutingPlan(
                shard_count=settings.evidence_shard_count,
                shard_strategy=settings.transaction_shard_strategy,
                shard_key="account_id",
                cross_shard_policy="avoid global scans; use account-local queries and compact evidence features",
            ),
            cache_policy=CachePolicy(
                backend=settings.cache_backend,
                ttl_seconds={
                    "transactions": settings.evidence_cache_ttl_seconds,
                    "rules": settings.investigation_rule_cache_ttl_seconds,
                    "rate_limits": settings.rate_limit_window_seconds,
                },
                stampede_protection=f"ttl jitter up to {settings.cache_stampede_jitter_seconds}s plus cache-aside fallback",
                invalidation=["transaction upsert", "active ruleset version change", "template or safety policy version change"],
            ),
            load_test_plan=LoadTestPlan(
                target_endpoint="POST /analyze-ticket",
                virtual_users=settings.load_test_virtual_users,
                duration_seconds=settings.load_test_duration_seconds,
                target_p95_ms=settings.load_test_target_p95_ms,
                success_criteria=[
                    "p95 latency under target",
                    "no uncontrolled 5xx responses",
                    "no database connection exhaustion",
                    "queue/dead-letter counts stay explainable",
                ],
            ),
        )

    def database_route(self, operation: str, read_your_write: bool = False) -> DatabaseRouteResponse:
        settings = get_settings()
        normalized = operation.lower()
        if normalized in {"write", "update", "insert", "delete"} or read_your_write:
            return DatabaseRouteResponse(
                operation=operation,
                target=settings.database_primary_url,
                consistency="strong primary read/write",
            )

        replicas = self._read_replicas()
        target = replicas[0] if replicas else settings.database_primary_url
        return DatabaseRouteResponse(
            operation=operation,
            target=target,
            consistency="eventual read replica",
        )

    def transaction_shard(self, account_id: str) -> dict[str, int | str]:
        settings = get_settings()
        shard_count = max(settings.evidence_shard_count, 1)
        digest = hashlib.sha256(account_id.encode("utf-8")).hexdigest()
        shard_id = int(digest[:8], 16) % shard_count
        return {
            "account_id": account_id,
            "shard_id": shard_id,
            "shard_count": shard_count,
            "strategy": settings.transaction_shard_strategy,
        }

    def _db_plan(self, service: str, read_replicas: list[str]) -> DatabaseScalingPlan:
        settings = get_settings()
        return DatabaseScalingPlan(
            service=service,
            write_target=settings.database_primary_url,
            read_targets=read_replicas,
            read_strategy="primary for writes and read-your-write; replicas for normal status/detail reads",
            pool_min_size=settings.database_pool_min_size,
            pool_max_size=settings.database_pool_max_size,
        )

    def _read_replicas(self) -> list[str]:
        settings = get_settings()
        return [item.strip() for item in settings.database_read_replica_urls.split(",") if item.strip()]


platform_scaling_service = PlatformScalingService()
