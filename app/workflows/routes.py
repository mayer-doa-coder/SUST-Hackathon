from __future__ import annotations

from fastapi import APIRouter

from app.workflows.schemas import WorkflowCompensateRequest, WorkflowResponse, WorkflowStartRequest, WorkflowStepRequest, WorkflowStepResponse
from app.workflows.service import workflow_service


router = APIRouter(prefix="/workflows", tags=["case-orchestration"])


@router.post("/analyze-ticket/start", response_model=WorkflowResponse)
async def start_workflow(payload: WorkflowStartRequest) -> WorkflowResponse:
    return workflow_service.start(payload)


@router.post("/{case_id}/steps/evidence-complete", response_model=WorkflowStepResponse)
async def evidence_complete(case_id: str, payload: WorkflowStepRequest) -> WorkflowStepResponse:
    return workflow_service.complete_step(case_id, "evidence", payload)


@router.post("/{case_id}/steps/investigation-complete", response_model=WorkflowStepResponse)
async def investigation_complete(case_id: str, payload: WorkflowStepRequest) -> WorkflowStepResponse:
    return workflow_service.complete_step(case_id, "investigation", payload)


@router.post("/{case_id}/steps/nlg-complete", response_model=WorkflowStepResponse)
async def nlg_complete(case_id: str, payload: WorkflowStepRequest) -> WorkflowStepResponse:
    return workflow_service.complete_step(case_id, "nlg", payload)


@router.post("/{case_id}/compensate", response_model=WorkflowResponse)
async def compensate_workflow(case_id: str, payload: WorkflowCompensateRequest) -> WorkflowResponse:
    return workflow_service.compensate(case_id, payload)


@router.post("/{case_id}/retry", response_model=WorkflowResponse)
async def retry_workflow(case_id: str) -> WorkflowResponse:
    return workflow_service.retry(case_id)


@router.get("/{case_id}", response_model=WorkflowResponse)
async def get_workflow(case_id: str) -> WorkflowResponse:
    return workflow_service.get(case_id)
