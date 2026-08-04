"""Shared base classes and helpers for HTTP DTOs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ApiBaseModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        extra="forbid",
        ser_json_timedelta="iso8601",
    )


class WriteApiBaseModel(ApiBaseModel):
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReadApiBaseModel(ApiBaseModel):
    pass


class ProblemDetails(ApiBaseModel):
    """RFC 7807 Problem Details payload."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    code: str | None = None
    correlation_id: str | None = None
    errors: dict[str, Any] | None = None


class IdResponse(ApiBaseModel):
    id: UUID


class HealthResponse(ApiBaseModel):
    status: str
    service: str
    version: str
    timestamp: datetime
