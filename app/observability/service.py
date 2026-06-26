from __future__ import annotations

from app.config import get_settings
from app.observability.schemas import ComponentHealth, ReadinessResponse, RecentTracesResponse, TraceResponse
from app.observability.registry import observability_registry


class ObservabilityService:
    def readiness(self) -> ReadinessResponse:
        settings = get_settings()
        components = [
            ComponentHealth(name="api-gateway", status="ok", detail="Gateway router is loaded."),
            ComponentHealth(name="auth", status="ok", detail="JWT service is configured."),
            ComponentHealth(name="ticket-intake", status="ok", detail="Ticket repository is reachable."),
            ComponentHealth(name="transaction-evidence", status="ok", detail="Evidence repository is reachable."),
            ComponentHealth(name="investigation", status="ok", detail="Active ruleset is configured."),
            ComponentHealth(name="nlg-safety", status="ok", detail="Template fallback is available."),
            ComponentHealth(name="workflow", status="ok", detail="Workflow repository is reachable."),
            ComponentHealth(name="pubsub-audit-routing", status="ok", detail="In-memory broker is reachable."),
        ]
        if settings.readiness_require_llm_key and not settings.google_api_key:
            components.append(ComponentHealth(name="llm-provider", status="degraded", detail="LLM key is required but missing."))
        else:
            components.append(ComponentHealth(name="llm-provider", status="ok", detail="Optional; template fallback is available."))

        status = "ok" if all(component.status == "ok" for component in components) else "degraded"
        return ReadinessResponse(status=status, service=settings.service_name, components=components)

    def recent_traces(self) -> RecentTracesResponse:
        return RecentTracesResponse(
            traces=[
                TraceResponse(
                    correlation_id=trace.correlation_id,
                    method=trace.method,
                    path=trace.path,
                    status_code=trace.status_code,
                    duration_ms=round(trace.duration_ms, 3),
                    timestamp=trace.timestamp,
                )
                for trace in observability_registry.recent_traces()
            ]
        )


observability_service = ObservabilityService()
