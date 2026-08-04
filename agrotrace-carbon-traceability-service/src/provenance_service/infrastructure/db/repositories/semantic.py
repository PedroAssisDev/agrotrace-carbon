"""SQLAlchemy implementations of the semantic-context repositories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from provenance_service.domain.semantic.entities import (
    CanonicalSnapshot,
    CanonicalSnapshotItem,
    OntologyResourceLink,
    SemanticIntegrationExecution,
)
from provenance_service.infrastructure.db.models.semantic import (
    CanonicalSnapshotItemModel,
    CanonicalSnapshotModel,
    OntologyResourceLinkModel,
    SemanticIntegrationExecutionModel,
)
from provenance_service.infrastructure.db.repositories import _mappers as M
from provenance_service.infrastructure.db.repositories._session_pending import (
    get_model_or_pending,
)


class SqlAlchemySemanticIntegrationExecutionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, execution: SemanticIntegrationExecution) -> None:
        self._session.add(M.to_semantic_integration_execution_model(execution))

    def get(
        self, semantic_integration_execution_id: UUID
    ) -> SemanticIntegrationExecution | None:
        m = get_model_or_pending(
            self._session,
            SemanticIntegrationExecutionModel,
            "semantic_integration_execution_id",
            semantic_integration_execution_id,
        )
        return M.from_semantic_integration_execution_model(m) if m else None

    def get_by_idempotency_key(self, key: str) -> SemanticIntegrationExecution | None:
        m = self._session.scalar(
            select(SemanticIntegrationExecutionModel).where(
                SemanticIntegrationExecutionModel.idempotency_key == key
            )
        )
        return M.from_semantic_integration_execution_model(m) if m else None

    def list_by_pipeline_run(
        self, pipeline_run_id: UUID
    ) -> list[SemanticIntegrationExecution]:
        rows = self._session.scalars(
            select(SemanticIntegrationExecutionModel).where(
                SemanticIntegrationExecutionModel.pipeline_run_id == pipeline_run_id
            )
        ).all()
        return [M.from_semantic_integration_execution_model(m) for m in rows]


class SqlAlchemyCanonicalSnapshotRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, snapshot: CanonicalSnapshot) -> None:
        self._session.add(M.to_canonical_snapshot_model(snapshot))

    def get(self, canonical_snapshot_id: UUID) -> CanonicalSnapshot | None:
        m = get_model_or_pending(
            self._session, CanonicalSnapshotModel, "canonical_snapshot_id", canonical_snapshot_id
        )
        return M.from_canonical_snapshot_model(m) if m else None

    def get_by_hash(self, snapshot_hash: str) -> CanonicalSnapshot | None:
        m = self._session.scalar(
            select(CanonicalSnapshotModel).where(
                CanonicalSnapshotModel.snapshot_hash == snapshot_hash
            )
        )
        return M.from_canonical_snapshot_model(m) if m else None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[CanonicalSnapshot]:
        rows = self._session.scalars(
            select(CanonicalSnapshotModel).where(
                CanonicalSnapshotModel.pipeline_run_id == pipeline_run_id
            )
        ).all()
        return [M.from_canonical_snapshot_model(m) for m in rows]

    def add_item(self, item: CanonicalSnapshotItem) -> None:
        self._session.add(M.to_canonical_snapshot_item_model(item))

    def list_items(
        self, canonical_snapshot_id: UUID
    ) -> list[CanonicalSnapshotItem]:
        rows = self._session.scalars(
            select(CanonicalSnapshotItemModel).where(
                CanonicalSnapshotItemModel.canonical_snapshot_id == canonical_snapshot_id
            )
        ).all()
        return [M.from_canonical_snapshot_item_model(m) for m in rows]


class SqlAlchemyOntologyResourceLinkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, link: OntologyResourceLink) -> None:
        self._session.add(M.to_ontology_resource_link_model(link))

    def get(self, ontology_resource_link_id: UUID) -> OntologyResourceLink | None:
        m = get_model_or_pending(
            self._session,
            OntologyResourceLinkModel,
            "ontology_resource_link_id",
            ontology_resource_link_id,
        )
        return M.from_ontology_resource_link_model(m) if m else None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[OntologyResourceLink]:
        rows = self._session.scalars(
            select(OntologyResourceLinkModel).where(
                OntologyResourceLinkModel.pipeline_run_id == pipeline_run_id
            )
        ).all()
        return [M.from_ontology_resource_link_model(m) for m in rows]
