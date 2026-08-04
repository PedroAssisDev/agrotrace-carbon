"""Middlewares for correlation id propagation and request logging."""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from provenance_service.infrastructure.observability.logging import (
    bind_correlation_id,
    get_current_correlation_id,
    get_logger,
)

__all__ = [
    "CORRELATION_HEADER",
    "CorrelationIdMiddleware",
    "get_current_correlation_id",
]

CORRELATION_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Read or generate ``X-Correlation-ID`` and propagate to logs and response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        cid = request.headers.get(CORRELATION_HEADER) or str(uuid.uuid4())
        bind_correlation_id(cid)

        log = get_logger("api")
        start = time.perf_counter()
        log.info(
            "request.start",
            method=request.method,
            path=request.url.path,
            query=str(request.url.query) if request.url.query else None,
            client=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000.0
            log.exception(
                "request.error",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
            )
            raise
        finally:
            bind_correlation_id(None)

        duration_ms = (time.perf_counter() - start) * 1000.0
        response.headers[CORRELATION_HEADER] = cid
        log.info(
            "request.end",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response
