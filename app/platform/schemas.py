from __future__ import annotations

from pydantic import BaseModel


class ServiceReplicaPlan(BaseModel):
    service: str
    replicas: int
    load_balancer_scope: str


class DatabaseScalingPlan(BaseModel):
    service: str
    write_target: str
    read_targets: list[str]
    read_strategy: str
    pool_min_size: int
    pool_max_size: int


class ShardRoutingPlan(BaseModel):
    shard_count: int
    shard_strategy: str
    shard_key: str
    cross_shard_policy: str


class CachePolicy(BaseModel):
    backend: str
    ttl_seconds: dict[str, int]
    stampede_protection: str
    invalidation: list[str]


class LoadTestPlan(BaseModel):
    target_endpoint: str
    virtual_users: int
    duration_seconds: int
    target_p95_ms: int
    success_criteria: list[str]


class ScalingPlanResponse(BaseModel):
    load_balancer: str
    service_replicas: list[ServiceReplicaPlan]
    database_scaling: list[DatabaseScalingPlan]
    shard_routing: ShardRoutingPlan
    cache_policy: CachePolicy
    load_test_plan: LoadTestPlan


class DatabaseRouteResponse(BaseModel):
    operation: str
    target: str
    consistency: str
