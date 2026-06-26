from __future__ import annotations

from fastapi import APIRouter

from app.nlg_service.schemas import NLGDraftRequest, NLGDraftResponse, SafetyValidateRequest, SafetyValidateResponse
from app.nlg_service.service import nlg_safety_service


router = APIRouter(tags=["nlg-safety"])


@router.post("/nlg/draft", response_model=NLGDraftResponse)
async def draft_nlg(payload: NLGDraftRequest) -> NLGDraftResponse:
    return await nlg_safety_service.draft(payload)


@router.post("/safety/validate", response_model=SafetyValidateResponse)
async def validate_safety(payload: SafetyValidateRequest) -> SafetyValidateResponse:
    return nlg_safety_service.validate_safety(payload)
