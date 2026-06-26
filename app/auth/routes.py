from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.schemas import JwksResponse, LoginRequest, LogoutResponse, RefreshRequest, TokenPairResponse
from app.auth.service import AuthError, auth_service


router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/login", response_model=TokenPairResponse)
async def login(payload: LoginRequest) -> TokenPairResponse:
    return auth_service.login(payload.username, payload.password)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(payload: RefreshRequest) -> TokenPairResponse:
    return auth_service.refresh(payload.refresh_token)


@router.post("/logout", response_model=LogoutResponse)
async def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> LogoutResponse:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthError("AUTH_REQUIRED", "A valid bearer token is required.", 401)
    auth_service.logout(credentials.credentials)
    return LogoutResponse(status="ok")


@router.get("/jwks", response_model=JwksResponse)
async def jwks() -> dict[str, list[dict[str, str]]]:
    return auth_service.jwks()
