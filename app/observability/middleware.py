from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.gateway.middleware import CORRELATION_ID_HEADER
from app.observability.registry import observability_registry


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000
        correlation_id = str(getattr(request.state, "correlation_id", request.headers.get(CORRELATION_ID_HEADER, "")))
        response.headers["X-Response-Time-ms"] = f"{duration_ms:.3f}"
        observability_registry.record_request(
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
