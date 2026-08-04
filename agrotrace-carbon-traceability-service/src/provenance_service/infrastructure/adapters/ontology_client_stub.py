"""No-op ontology client used until the real HTTP integration is wired up."""

from __future__ import annotations

from typing import Any

from provenance_service.application.ports import (
    OntologyClient,
    OntologyResourceMeta,
    PublicationReceipt,
)
from provenance_service.domain.shared.time import utcnow
from provenance_service.infrastructure.observability import get_logger


class StubOntologyClient(OntologyClient):
    def __init__(self) -> None:
        self._log = get_logger("adapter.ontology")

    def publish_calculation_result(
        self,
        *,
        target_graph_name: str,
        ontology_name: str,
        ontology_version: str,
        payload: dict[str, Any],
    ) -> PublicationReceipt:
        receipt = PublicationReceipt(
            ontology_uri=f"urn:stub:{ontology_name}/{ontology_version}",
            graph_name=target_graph_name,
            ontology_version=ontology_version,
            published_at=utcnow(),
            transport_metadata={"adapter": "stub"},
        )
        self._log.info(
            "ontology.publish_stub",
            target_graph_name=target_graph_name,
            ontology_name=ontology_name,
            ontology_version=ontology_version,
            payload_keys=sorted(payload.keys()),
        )
        return receipt

    def fetch_resource_metadata(self, iri: str) -> OntologyResourceMeta | None:
        self._log.info("ontology.fetch_resource_stub", iri=iri)
        return None
