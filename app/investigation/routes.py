from __future__ import annotations

from fastapi import APIRouter

from app.investigation.schemas import ActiveRulesResponse, InvestigationDecisionResponse, InvestigationEvaluateRequest
from app.investigation.service import investigation_service


router = APIRouter(tags=["investigation"])


@router.post("/investigations/evaluate", response_model=InvestigationDecisionResponse)
async def evaluate_investigation(payload: InvestigationEvaluateRequest) -> InvestigationDecisionResponse:
    return investigation_service.evaluate_response(payload)


@router.get("/rules/active-version", response_model=ActiveRulesResponse)
async def active_rule_version() -> ActiveRulesResponse:
    return investigation_service.active_rules()
