"""HTTP exception handlers translating domain errors into RFC 7807 responses."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from provenance_service.domain.shared.errors import (
    AlreadyExistsError,
    AppendOnlyViolationError,
    DomainError,
    IdempotencyConflictError,
    InvariantViolationError,
    NotFoundError,
)
from provenance_service.infrastructure.observability import get_logger
from provenance_service.infrastructure.observability.middleware import (
    get_current_correlation_id,
)

PROBLEM_CONTENT_TYPE = "application/problem+json"

_log = get_logger("api.errors")


def _problem(
    *,
    title: str,
    status_code: int,
    detail: str | None = None,
    code: str | None = None,
    type_: str = "about:blank",
    errors: dict[str, Any] | None = None,
    instance: str | None = None,
) -> JSONResponse:
    payload: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status_code,
    }
    if detail is not None:
        payload["detail"] = detail
    if code is not None:
        payload["code"] = code
    if errors is not None:
        payload["errors"] = errors
    if instance is not None:
        payload["instance"] = instance
    correlation_id = get_current_correlation_id()
    if correlation_id:
        payload["correlation_id"] = correlation_id
    return JSONResponse(
        content=jsonable_encoder(payload),
        status_code=status_code,
        media_type=PROBLEM_CONTENT_TYPE,
    )


def install_exception_handlers(app: FastAPI) -> None:
    """Register all domain → HTTP error mappings on the FastAPI app."""

    @app.exception_handler(NotFoundError)
    async def _handle_not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return _problem(
            title="Not Found",
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
            code=exc.__class__.__name__,
            errors=exc.details or None,
        )

    @app.exception_handler(AlreadyExistsError)
    async def _handle_already_exists(_: Request, exc: AlreadyExistsError) -> JSONResponse:
        return _problem(
            title="Resource Already Exists",
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
            code=exc.__class__.__name__,
            errors=exc.details or None,
        )

    @app.exception_handler(IdempotencyConflictError)
    async def _handle_idempotency_conflict(
        _: Request, exc: IdempotencyConflictError
    ) -> JSONResponse:
        return _problem(
            title="Idempotency Conflict",
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
            code=exc.__class__.__name__,
            errors=exc.details or None,
        )

    @app.exception_handler(InvariantViolationError)
    async def _handle_invariant(_: Request, exc: InvariantViolationError) -> JSONResponse:
        return _problem(
            title="Invariant Violation",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
            code=exc.__class__.__name__,
            errors=exc.details or None,
        )

    @app.exception_handler(AppendOnlyViolationError)
    async def _handle_append_only(
        _: Request, exc: AppendOnlyViolationError
    ) -> JSONResponse:
        return _problem(
            title="Append-Only Violation",
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
            code=exc.__class__.__name__,
            errors=exc.details or None,
        )

    @app.exception_handler(DomainError)
    async def _handle_domain(_: Request, exc: DomainError) -> JSONResponse:
        return _problem(
            title="Domain Error",
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
            code=exc.__class__.__name__,
            errors=exc.details or None,
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _problem(
            title="Validation Error",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Request body failed validation",
            code="ValidationError",
            errors={"items": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(IntegrityError)
    async def _handle_integrity(_: Request, exc: IntegrityError) -> JSONResponse:
        _log.warning("db.integrity_error", error=str(exc))
        return _problem(
            title="Database Integrity Error",
            status_code=status.HTTP_409_CONFLICT,
            detail="Database constraint violated. The operation may conflict with existing data.",
            code="IntegrityError",
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        _log.exception("api.unhandled_exception", error=str(exc))
        return _problem(
            title="Internal Server Error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
            code=exc.__class__.__name__,
        )
