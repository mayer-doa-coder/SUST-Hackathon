from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.auth.routes import router as auth_router
from app.config import get_settings
from app.evidence.routes import router as evidence_router
from app.gateway.middleware import CorrelationIdMiddleware, InMemoryRateLimitMiddleware
from app.gateway.routes import router as gateway_router
from app.investigation.routes import router as investigation_router
from app.messaging.routes import router as messaging_router
from app.nlg_service.routes import router as nlg_safety_router
from app.observability.middleware import ObservabilityMiddleware
from app.observability.routes import router as observability_router
from app.platform.routes import router as platform_router
from app.tickets.routes import router as ticket_router
from app.workflows.routes import router as workflow_router


settings = get_settings()

app = FastAPI(
    title="QueueStorm Investigator",
    version=settings.app_version,
)

app.add_middleware(InMemoryRateLimitMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(ObservabilityMiddleware)
register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(evidence_router)
app.include_router(investigation_router)
app.include_router(messaging_router)
app.include_router(nlg_safety_router)
app.include_router(observability_router)
app.include_router(platform_router)
app.include_router(ticket_router)
app.include_router(workflow_router)
app.include_router(gateway_router)

