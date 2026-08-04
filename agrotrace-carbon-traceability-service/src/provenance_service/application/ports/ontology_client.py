"""Outbound port for the ontology service."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class PublicationReceipt:
    ontology_uri: str
    graph_name: str
    ontology_version: str
    published_at: datetime
    transport_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OntologyResourceMeta:
    iri: str
    ontology_version: str
    rdf_class: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class OntologyClient(Protocol):
    """Publishes calculation results into the ontology / triple store."""

    def publish_calculation_result(
        self,
        *,
        target_graph_name: str,
        ontology_name: str,
        ontology_version: str,
        payload: dict[str, Any],
    ) -> PublicationReceipt: ...

    def fetch_resource_metadata(self, iri: str) -> OntologyResourceMeta | None: ...
