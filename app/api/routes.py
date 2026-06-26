from fastapi import APIRouter

from app.api.schemas import AnalyzeTicketRequest, AnalyzeTicketResponse
from app.services.analysis import analyze_ticket


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze-ticket", response_model=AnalyzeTicketResponse)
async def analyze_ticket_route(payload: AnalyzeTicketRequest) -> AnalyzeTicketResponse:
    return await analyze_ticket(payload)

