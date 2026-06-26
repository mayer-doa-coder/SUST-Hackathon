from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)

    model_config = ConfigDict(extra="ignore")


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)

    model_config = ConfigDict(extra="ignore")


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    roles: list[str]


class LogoutResponse(BaseModel):
    status: str


class JwksResponse(BaseModel):
    keys: list[dict[str, str]]
