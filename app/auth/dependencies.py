from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.service import AuthError, auth_service
from app.config import get_settings


bearer_scheme = HTTPBearer(auto_error=False)


def require_roles(*allowed_roles: str) -> Callable:
    async def dependency(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> dict | None:
        settings = get_settings()
        if not settings.auth_required:
            return None

        if credentials is None or credentials.scheme.lower() != "bearer":
            raise AuthError("AUTH_REQUIRED", "A valid bearer token is required.", 401)

        payload = auth_service.verify(credentials.credentials, token_type="access")
        roles = set(str(role) for role in payload.get("roles", []))
        if allowed_roles and not roles.intersection(allowed_roles):
            raise AuthError("FORBIDDEN", "The authenticated user does not have access to this endpoint.", 403)

        request.state.auth_subject = payload.get("sub")
        request.state.auth_roles = list(roles)
        return payload

    return dependency
