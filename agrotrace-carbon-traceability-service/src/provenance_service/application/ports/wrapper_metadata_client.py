"""Outbound port for fetching wrapper-version metadata from the wrappers service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class WrapperVersionMeta:
    wrapper_name: str
    wrapper_version: str
    source_layout_name: str
    source_layout_version: str | None
    schema_version: str | None
    code_hash: str | None
    transport_metadata: dict[str, Any] = field(default_factory=dict)


class WrapperMetadataClient(Protocol):
    """Reads wrapper definitions from the wrappers service.

    The provenance service caches a local immutable snapshot of these in
    ``pipeline.wrapper_definition``; this port is used to lazily resolve a
    wrapper version when a wrapper_execution is recorded but the local cache
    does not yet know about that name/version pair.
    """

    def get_wrapper_version(
        self, name: str, version: str
    ) -> WrapperVersionMeta | None: ...
