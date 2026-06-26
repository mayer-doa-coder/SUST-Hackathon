from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException

from app.api.schemas import ErrorBody, ErrorResponse
from app.auth.service import AuthError
from app.evidence.repository import TransactionNotFoundError
from app.gateway.upstream import GatewayUpstreamError
from app.tickets.repository import TicketNotFoundError
from app.workflows.repository import WorkflowConflictError, WorkflowNotFoundError


def _extract_ticket_id(body: Any) -> str | None:
    if isinstance(body, dict):
        ticket_id = body.get("ticket_id")
        if isinstance(ticket_id, str) and ticket_id.strip():
            return ticket_id
    return None


def _error_response(
    status_code: int,
    code: str,
    message: str,
    ticket_id: str | None = None,
) -> JSONResponse:
    payload = ErrorResponse(error=ErrorBody(code=code, message=message, ticket_id=ticket_id))
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


async def _try_parse_request_body(request: Request) -> Any:
    try:
        body = await request.body()
    except Exception:
        return None
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:
        return None


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthError)
    async def auth_handler(_: Request, exc: AuthError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(GatewayUpstreamError)
    async def gateway_upstream_handler(_: Request, exc: GatewayUpstreamError) -> JSONResponse:
        return _error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(TicketNotFoundError)
    async def ticket_not_found_handler(_: Request, exc: TicketNotFoundError) -> JSONResponse:
        return _error_response(404, "TICKET_NOT_FOUND", "Ticket analysis case was not found.", str(exc))

    @app.exception_handler(TransactionNotFoundError)
    async def transaction_not_found_handler(_: Request, exc: TransactionNotFoundError) -> JSONResponse:
        return _error_response(404, "TRANSACTION_NOT_FOUND", "Transaction was not found.", str(exc))

    @app.exception_handler(WorkflowNotFoundError)
    async def workflow_not_found_handler(_: Request, exc: WorkflowNotFoundError) -> JSONResponse:
        return _error_response(404, "WORKFLOW_NOT_FOUND", "Workflow case was not found.", str(exc))

    @app.exception_handler(WorkflowConflictError)
    async def workflow_conflict_handler(_: Request, exc: WorkflowConflictError) -> JSONResponse:
        return _error_response(409, "WORKFLOW_CONFLICT", exc.message)

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        raw_body = await _try_parse_request_body(request)
        ticket_id = _extract_ticket_id(raw_body)

        error_types = {error.get("type", "") for error in exc.errors()}
        missing_required = any(error_type.endswith("missing") for error_type in error_types)
        enum_error = any("enum" in error_type for error_type in error_types)
        json_error = any("json" in error_type for error_type in error_types)

        if json_error:
            return _error_response(400, "MALFORMED_JSON", "Request body must contain valid JSON.", ticket_id)

        for error in exc.errors():
            field_name = ".".join(str(part) for part in error.get("loc", []) if part != "body")
            message = error.get("msg", "Invalid request.")
            if field_name == "complaint" and ("empty" in message.lower() or "not be empty" in message.lower()):
                return _error_response(422, "EMPTY_COMPLAINT", "Complaint must be a non-empty string.", ticket_id)
            if field_name == "ticket_id" and ("not be empty" in message.lower()):
                return _error_response(422, "INVALID_FIELD_TYPE", "ticket_id must be a non-empty string.", ticket_id)

        if missing_required:
            return _error_response(
                400,
                "MISSING_REQUIRED_FIELD",
                "Request must include the required fields ticket_id and complaint.",
                ticket_id,
            )

        if enum_error:
            return _error_response(
                422,
                "INVALID_ENUM_VALUE",
                "One or more optional enum fields contain invalid values.",
                ticket_id,
            )

        return _error_response(
            400,
            "INVALID_FIELD_TYPE",
            "Request contains missing or invalid field types.",
            ticket_id,
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(_: Request, exc: ValidationError) -> JSONResponse:
        return _error_response(500, "INTERNAL_ERROR", "Response validation failed unexpectedly.")

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, _: Exception) -> JSONResponse:
        raw_body = await _try_parse_request_body(request)
        return _error_response(
            500,
            "INTERNAL_ERROR",
            "The service could not complete the request.",
            _extract_ticket_id(raw_body),
        )

