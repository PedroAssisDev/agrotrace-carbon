"""No-op wrapper metadata client (returns nothing).

The real adapter will hit the wrappers service over HTTP. The stub never
resolves a definition, forcing callers to register wrapper definitions
explicitly via the dedicated endpoint until that integration is in place.
"""

from __future__ import annotations

from provenance_service.application.ports import (
    WrapperMetadataClient,
    WrapperVersionMeta,
)
from provenance_service.infrastructure.observability import get_logger


class StubWrapperMetadataClient(WrapperMetadataClient):
    def __init__(self) -> None:
        self._log = get_logger("adapter.wrapper_metadata")

    def get_wrapper_version(self, name: str, version: str) -> WrapperVersionMeta | None:
        self._log.info("wrapper_metadata.fetch_stub", name=name, version=version)
        return None
