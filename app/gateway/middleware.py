from __future__ import annotations

import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api.schemas import ErrorBody, ErrorResponse
from app.config import get_settings


CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        if not settings.rate_limit_enabled or request.url.path.startswith("/health"):
            return await call_next(request)

        identity = request.headers.get("Authorization") or (request.client.host if request.client else "unknown")
        now = time.monotonic()
        window_start = now - settings.rate_limit_window_seconds
        bucket = self.requests[identity]

        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= settings.rate_limit_requests:
            payload = ErrorResponse(
                error=ErrorBody(
                    code="RATE_LIMIT_EXCEEDED",
                    message="Too many requests. Please retry after the rate-limit window resets.",
                )
            )
            return JSONResponse(
                status_code=429,
                content=payload.model_dump(mode="json"),
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )

        bucket.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(settings.rate_limit_requests - len(bucket), 0))
        return response
