"""Semantic bounded-context tables (prefixed names for single-schema SQLite)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from provenance_service.infrastructure.db.models.base import (
    PUBLICATION_STAGE_T,
    SEMANTIC_EXECUTION_STATUS_T,
    Base,
    UUID_T,
)


def _sem(name: str) -> str:
    return f"semantic_{name}"


def _pl(name: str) -> str:
    return f"pipeline_{name}"


def _pc(name: str) -> str:
    return f"prov_core_{name}"


def _rep(name: str) -> str:
    return f"reporting_{name}"


class SemanticIntegrationExecutionModel(Base):
    __tablename__ = _sem("semantic_integration_execution")
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key", name="uq_semantic_integration_execution_idempotency_key"
        ),
        UniqueConstraint(
            "prov_activity_id", name="uq_semantic_integration_execution_prov_activity_id"
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_semantic_integration_execution_finished_at_ge_started_at",
        ),
        Index("ix_semantic_integration_execution_pipeline_run_id", "pipeline_run_id"),
    )

    semantic_integration_execution_id: Mapped[UUID] = mapped_column(
        UUID_T, primary_key=True
    )
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_semantic_integration_execution_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    prov_activity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_activity')}.activity_id",
            name="fk_semantic_integration_execution_prov_activity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    normalized_batch_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('normalized_batch')}.normalized_batch_id",
            name="fk_semantic_integration_execution_normalized_batch_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    ontology_name: Mapped[str] = mapped_column(String(128), nullable=False)
    ontology_version: Mapped[str] = mapped_column(String(64), nullable=False)
    mapping_rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_status: Mapped[str] = mapped_column(SEMANTIC_EXECUTION_STATUS_T, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triples_generated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class CanonicalSnapshotModel(Base):
    __tablename__ = _sem("canonical_snapshot")
    __table_args__ = (
        UniqueConstraint("prov_entity_id", name="uq_canonical_snapshot_prov_entity_id"),
        UniqueConstraint("snapshot_hash", name="uq_canonical_snapshot_snapshot_hash"),
        Index("ix_canonical_snapshot_pipeline_run_id", "pipeline_run_id"),
        Index("ix_canonical_snapshot_graph_name", "graph_name"),
    )

    canonical_snapshot_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_canonical_snapshot_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    prov_entity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_canonical_snapshot_prov_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    semantic_integration_execution_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_sem('semantic_integration_execution')}.semantic_integration_execution_id",
            name="fk_canonical_snapshot_semantic_integration_execution_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    graph_name: Mapped[str] = mapped_column(String(256), nullable=False)
    snapshot_label: Mapped[str] = mapped_column(String(256), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    canonical_schema_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    item_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snapshot_payload_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    storage_uri: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    reporting_period_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_rep('period')}.reporting_period_id",
            name="fk_canonical_snapshot_reporting_period_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class CanonicalSnapshotItemModel(Base):
    __tablename__ = _sem("canonical_snapshot_item")
    __table_args__ = (
        UniqueConstraint(
            "canonical_snapshot_id",
            "item_key",
            name="uq_canonical_snapshot_item_snapshot_id_item_key",
        ),
        Index("ix_canonical_snapshot_item_canonical_snapshot_id", "canonical_snapshot_id"),
        Index("ix_canonical_snapshot_item_item_key", "item_key"),
    )

    canonical_snapshot_item_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    canonical_snapshot_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_sem('canonical_snapshot')}.canonical_snapshot_id",
            name="fk_canonical_snapshot_item_canonical_snapshot_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    item_key: Mapped[str] = mapped_column(String(256), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    item_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)


class OntologyResourceLinkModel(Base):
    __tablename__ = _sem("ontology_resource_link")
    __table_args__ = (
        Index("ix_ontology_resource_link_pipeline_run_id", "pipeline_run_id"),
        Index("ix_ontology_resource_link_ontology_uri", "ontology_uri"),
        Index("ix_ontology_resource_link_canonical_snapshot_id", "canonical_snapshot_id"),
    )

    ontology_resource_link_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_ontology_resource_link_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    prov_entity_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_ontology_resource_link_prov_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    canonical_snapshot_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_sem('canonical_snapshot')}.canonical_snapshot_id",
            name="fk_ontology_resource_link_canonical_snapshot_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    ontology_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    rdf_class: Mapped[str | None] = mapped_column(String(256), nullable=True)
    graph_name: Mapped[str] = mapped_column(String(256), nullable=False)
    ontology_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    publication_stage: Mapped[str] = mapped_column(PUBLICATION_STAGE_T, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )
