from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from app.api.schemas import AnalyzeTicketRequest, AnalyzeTicketResponse
from app.services.analysis import analyze_ticket


router = APIRouter()


@router.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze-ticket", response_model=AnalyzeTicketResponse)
async def analyze_ticket_route(payload: AnalyzeTicketRequest) -> AnalyzeTicketResponse:
    return await analyze_ticket(payload)

