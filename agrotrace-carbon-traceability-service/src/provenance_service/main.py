"""FastAPI application entry-point.

The full router wiring lives in :mod:`provenance_service.interfaces.api.v1` and
is registered here at import time. ``run`` is exposed as a console-script for
local development and containerised execution.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI
from sqlalchemy import text

from provenance_service import __version__ as service_version
from provenance_service.infrastructure.config import get_settings
from provenance_service.infrastructure.db.session import get_engine
from provenance_service.infrastructure.observability import (
    CorrelationIdMiddleware,
    configure_logging,
    get_logger,
    metrics_response,
)
from provenance_service.interfaces.api.errors import install_exception_handlers
from provenance_service.interfaces.api.schemas.common import HealthResponse
from provenance_service.interfaces.api.v1 import build_v1_router


def _create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(
        service_name=settings.service_name,
        environment=settings.environment,
        level=settings.log_level,
    )
    log = get_logger("bootstrap")

    enable_outbox_worker = (
        os.getenv("PROV_ENABLE_OUTBOX_WORKER", "true").lower() in {"1", "true", "yes"}
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        log.info(
            "service.startup",
            service=settings.service_name,
            environment=settings.environment,
            version=service_version,
        )
        worker = None
        if enable_outbox_worker:
            from provenance_service.infrastructure.adapters import LoggingEventPublisher
            from provenance_service.infrastructure.outbox import (
                OutboxDispatcher,
                OutboxWorker,
            )
            from provenance_service.interfaces.api.deps import get_uow_factory

            dispatcher = OutboxDispatcher(
                get_uow_factory(),
                LoggingEventPublisher(),
                batch_size=settings.outbox_batch_size,
            )
            worker = OutboxWorker(
                dispatcher,
                poll_interval_seconds=settings.outbox_poll_interval_seconds,
            )
            worker.start()
        try:
            yield
        finally:
            if worker is not None:
                worker.stop()
            try:
                get_engine().dispose()
            except Exception:  # noqa: BLE001
                log.exception("service.engine_dispose_failed")
            log.info("service.shutdown", service=settings.service_name)

    app = FastAPI(
        title="AgroTrace Carbon Provenance Service",
        version=service_version,
        description=(
            "Append-only provenance ledger for AgroTrace Carbon: data lineage, "
            "wrapper executions, canonical snapshots, calculations, reviews, "
            "publications and integrity hashes."
        ),
        root_path=settings.api_root_path,
        lifespan=lifespan,
    )

    app.add_middleware(CorrelationIdMiddleware)

    @app.get(
        "/healthz",
        tags=["health"],
        response_model=HealthResponse,
        summary="Liveness probe",
    )
    def healthz() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=settings.service_name,
            version=service_version,
            timestamp=datetime.now(timezone.utc),
        )

    @app.get(
        "/readyz",
        tags=["health"],
        response_model=HealthResponse,
        summary="Readiness probe (checks DB)",
    )
    def readyz() -> HealthResponse:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return HealthResponse(
            status="ready",
            service=settings.service_name,
            version=service_version,
            timestamp=datetime.now(timezone.utc),
        )

    @app.get("/metrics", tags=["health"], include_in_schema=False)
    def metrics() -> object:
        return metrics_response()

    install_exception_handlers(app)
    app.include_router(build_v1_router())

    return app


app = _create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "provenance_service.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.environment == "local",
        access_log=False,
    )


if __name__ == "__main__":  # pragma: no cover
    run()
