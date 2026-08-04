"""v1 API routers (pipeline, prov, semantic, calculation, audit)."""

from fastapi import APIRouter

from provenance_service.interfaces.api.v1 import (
    audit,
    calculation,
    pipeline,
    prov,
    reporting,
    semantic,
)


def build_v1_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")
    router.include_router(pipeline.router)
    router.include_router(prov.router)
    router.include_router(semantic.router)
    router.include_router(calculation.router)
    router.include_router(reporting.router)
    router.include_router(audit.router)
    return router


__all__ = ["build_v1_router"]
