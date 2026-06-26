from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4


class TokenError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii"))


def _json_encode(data: dict[str, Any]) -> bytes:
    return json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sign(signing_input: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def encode_jwt(
    subject: str,
    roles: list[str],
    token_type: str,
    secret: str,
    issuer: str,
    audience: str,
    expires_in_seconds: int,
) -> tuple[str, dict[str, Any]]:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "aud": audience,
        "exp": int((now + timedelta(seconds=expires_in_seconds)).timestamp()),
        "iat": int(now.timestamp()),
        "iss": issuer,
        "jti": str(uuid4()),
        "roles": roles,
        "sub": subject,
        "typ": token_type,
    }
    header = {"alg": "HS256", "kid": "default-hs256", "typ": "JWT"}
    signing_input = f"{_b64url_encode(_json_encode(header))}.{_b64url_encode(_json_encode(payload))}"
    token = f"{signing_input}.{_sign(signing_input, secret)}"
    return token, payload


def decode_jwt(token: str, secret: str, issuer: str, audience: str, token_type: str | None = None) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise TokenError("INVALID_TOKEN", "Bearer token is not a valid JWT.")

    signing_input = f"{parts[0]}.{parts[1]}"
    expected_signature = _sign(signing_input, secret)
    if not hmac.compare_digest(expected_signature, parts[2]):
        raise TokenError("INVALID_TOKEN", "Bearer token signature is invalid.")

    try:
        header = json.loads(_b64url_decode(parts[0]))
        payload = json.loads(_b64url_decode(parts[1]))
    except Exception as exc:
        raise TokenError("INVALID_TOKEN", "Bearer token payload is invalid.") from exc

    if header.get("alg") != "HS256":
        raise TokenError("INVALID_TOKEN", "Bearer token algorithm is not supported.")
    if payload.get("iss") != issuer or payload.get("aud") != audience:
        raise TokenError("INVALID_TOKEN", "Bearer token issuer or audience is invalid.")
    if token_type and payload.get("typ") != token_type:
        raise TokenError("INVALID_TOKEN", "Bearer token type is invalid.")
    if int(payload.get("exp", 0)) <= int(datetime.now(UTC).timestamp()):
        raise TokenError("TOKEN_EXPIRED", "Bearer token has expired.")
    if not isinstance(payload.get("roles"), list):
        raise TokenError("INVALID_TOKEN", "Bearer token roles claim is invalid.")

    return payload
