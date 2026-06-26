from __future__ import annotations

from fastapi import APIRouter

from app.platform.schemas import DatabaseRouteResponse, ScalingPlanResponse
from app.platform.service import platform_scaling_service


router = APIRouter(prefix="/platform", tags=["platform-scaling"])


@router.get("/scaling-plan", response_model=ScalingPlanResponse)
async def scaling_plan() -> ScalingPlanResponse:
    return platform_scaling_service.scaling_plan()


@router.get("/database-route", response_model=DatabaseRouteResponse)
async def database_route(operation: str = "read", read_your_write: bool = False) -> DatabaseRouteResponse:
    return platform_scaling_service.database_route(operation, read_your_write)


@router.get("/transaction-shards/{account_id}")
async def transaction_shard(account_id: str) -> dict[str, int | str]:
    return platform_scaling_service.transaction_shard(account_id)
