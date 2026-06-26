from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass, field

from app.auth.schemas import TokenPairResponse
from app.auth.tokens import TokenError, decode_jwt, encode_jwt
from app.config import Settings, get_settings


class AuthError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 401) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


@dataclass
class AuthService:
    settings: Settings = field(default_factory=get_settings)
    revoked_token_ids: set[str] = field(default_factory=set)

    def _roles(self) -> list[str]:
        return [role.strip() for role in self.settings.auth_demo_roles.split(",") if role.strip()]

    def login(self, username: str, password: str) -> TokenPairResponse:
        valid_username = hmac.compare_digest(username, self.settings.auth_demo_username)
        valid_password = hmac.compare_digest(password, self.settings.auth_demo_password)
        if not valid_username or not valid_password:
            raise AuthError("INVALID_CREDENTIALS", "Username or password is invalid.", 401)

        roles = self._roles()
        access_token, _ = encode_jwt(
            username,
            roles,
            "access",
            self.settings.auth_jwt_secret,
            self.settings.auth_issuer,
            self.settings.auth_audience,
            self.settings.auth_access_token_seconds,
        )
        refresh_token, _ = encode_jwt(
            username,
            roles,
            "refresh",
            self.settings.auth_jwt_secret,
            self.settings.auth_issuer,
            self.settings.auth_audience,
            self.settings.auth_refresh_token_seconds,
        )
        return TokenPairResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.settings.auth_access_token_seconds,
            roles=roles,
        )

    def refresh(self, refresh_token: str) -> TokenPairResponse:
        payload = self.verify(refresh_token, token_type="refresh")
        return self.login(str(payload["sub"]), self.settings.auth_demo_password)

    def logout(self, token: str) -> None:
        payload = self.verify(token, token_type=None)
        self.revoked_token_ids.add(str(payload["jti"]))

    def verify(self, token: str, token_type: str | None = "access") -> dict:
        try:
            payload = decode_jwt(
                token,
                self.settings.auth_jwt_secret,
                self.settings.auth_issuer,
                self.settings.auth_audience,
                token_type,
            )
        except TokenError as exc:
            raise AuthError(exc.code, exc.message, 401) from exc

        if payload.get("jti") in self.revoked_token_ids:
            raise AuthError("TOKEN_REVOKED", "Bearer token has been revoked.", 401)
        return payload

    def jwks(self) -> dict[str, list[dict[str, str]]]:
        digest = hashlib.sha256(self.settings.auth_jwt_secret.encode("utf-8")).digest()
        key = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return {
            "keys": [
                {
                    "kty": "oct",
                    "kid": "default-hs256",
                    "alg": "HS256",
                    "use": "sig",
                    "k": key,
                }
            ]
        }


auth_service = AuthService()
