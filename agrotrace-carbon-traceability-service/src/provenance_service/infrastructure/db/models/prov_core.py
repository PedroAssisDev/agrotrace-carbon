"""PROV-core tables (prefixed names for single-schema SQLite)."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from provenance_service.infrastructure.db.models.base import (
    PROV_ACTIVITY_TYPE_T,
    PROV_AGENT_TYPE_T,
    PROV_BUNDLE_STATUS_T,
    PROV_BUNDLE_TYPE_T,
    PROV_ENTITY_TYPE_T,
    Base,
    UUID_T,
)


def _pc(name: str) -> str:
    return f"prov_core_{name}"


def _pl(name: str) -> str:
    return f"pipeline_{name}"


class ProvBundleModel(Base):
    __tablename__ = _pc("prov_bundle")
    __table_args__ = (
        Index("ix_prov_bundle_pipeline_run_id", "pipeline_run_id"),
        Index("ix_prov_bundle_status", "status"),
    )

    bundle_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_prov_bundle_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    bundle_type: Mapped[str] = mapped_column(PROV_BUNDLE_TYPE_T, nullable=False)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(PROV_BUNDLE_STATUS_T, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class ProvEntityModel(Base):
    __tablename__ = _pc("prov_entity")
    __table_args__ = (
        Index("ix_prov_entity_bundle_id", "bundle_id"),
        Index("ix_prov_entity_pipeline_run_id", "pipeline_run_id"),
        Index("ix_prov_entity_entity_type", "entity_type"),
        Index("ix_prov_entity_business_key", "business_key"),
        Index("ix_prov_entity_entity_ref", "entity_kind", "entity_ref_id"),
    )

    entity_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    bundle_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_bundle')}.bundle_id",
            name="fk_prov_entity_bundle_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_prov_entity_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(PROV_ENTITY_TYPE_T, nullable=False)
    entity_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_ref_id: Mapped[UUID | None] = mapped_column(UUID_T, nullable=True)
    business_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    version_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class ProvActivityModel(Base):
    __tablename__ = _pc("prov_activity")
    __table_args__ = (
        Index("ix_prov_activity_bundle_id", "bundle_id"),
        Index("ix_prov_activity_pipeline_run_id", "pipeline_run_id"),
        Index("ix_prov_activity_activity_type", "activity_type"),
        Index("ix_prov_activity_business_key", "business_key"),
    )

    activity_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    bundle_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_bundle')}.bundle_id",
            name="fk_prov_activity_bundle_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    pipeline_run_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pl('pipeline_run')}.pipeline_run_id",
            name="fk_prov_activity_pipeline_run_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    activity_type: Mapped[str] = mapped_column(PROV_ACTIVITY_TYPE_T, nullable=False)
    business_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    software_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class ProvAgentModel(Base):
    __tablename__ = _pc("prov_agent")
    __table_args__ = (
        UniqueConstraint(
            "agent_type",
            "external_reference",
            name="uq_prov_agent_agent_type_external_reference",
        ),
        Index("ix_prov_agent_external_reference", "external_reference"),
    )

    agent_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    agent_type: Mapped[str] = mapped_column(PROV_AGENT_TYPE_T, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    organization_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class ProvUsedModel(Base):
    __tablename__ = _pc("prov_used")
    __table_args__ = (
        UniqueConstraint(
            "activity_id",
            "entity_id",
            "role",
            name="uq_prov_used_activity_id_entity_id_role",
        ),
        Index("ix_prov_used_entity_id", "entity_id"),
    )

    used_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    activity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_activity')}.activity_id",
            name="fk_prov_used_activity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    entity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_prov_used_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class ProvGeneratedModel(Base):
    __tablename__ = _pc("prov_generated")
    __table_args__ = (
        UniqueConstraint("entity_id", "activity_id", name="uq_prov_generated_entity_id_activity_id"),
        Index("ix_prov_generated_activity_id", "activity_id"),
    )

    generated_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    entity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_prov_generated_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    activity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_activity')}.activity_id",
            name="fk_prov_generated_activity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class ProvDerivedFromModel(Base):
    __tablename__ = _pc("prov_derived_from")
    __table_args__ = (
        UniqueConstraint(
            "generated_entity_id",
            "source_entity_id",
            "derivation_type",
            name="uq_prov_derived_from_generated_entity_id_source_entity_id_derivation_type",
        ),
        Index("ix_prov_derived_from_source_entity_id", "source_entity_id"),
    )

    derived_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    generated_entity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_prov_derived_from_generated_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    source_entity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_prov_derived_from_source_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    derivation_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class ProvAssociatedWithModel(Base):
    __tablename__ = _pc("prov_associated_with")
    __table_args__ = (
        UniqueConstraint(
            "activity_id",
            "agent_id",
            "role",
            name="uq_prov_associated_with_activity_id_agent_id_role",
        ),
        Index("ix_prov_associated_with_agent_id", "agent_id"),
    )

    association_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    activity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_activity')}.activity_id",
            name="fk_prov_associated_with_activity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    agent_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_agent')}.agent_id",
            name="fk_prov_associated_with_agent_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    role: Mapped[str | None] = mapped_column(String(128), nullable=True)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class ProvRevisionModel(Base):
    __tablename__ = _pc("prov_revision")
    __table_args__ = (
        UniqueConstraint(
            "previous_entity_id",
            "new_entity_id",
            name="uq_prov_revision_previous_entity_id_new_entity_id",
        ),
        Index("ix_prov_revision_new_entity_id", "new_entity_id"),
    )

    revision_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    previous_entity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_prov_revision_previous_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    new_entity_id: Mapped[UUID] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_prov_revision_new_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    revision_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    revised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, nullable=False, server_default=text("'{}'")
    )


class ProvAttributeModel(Base):
    __tablename__ = _pc("prov_attribute")
    __table_args__ = (
        Index("ix_prov_attribute_entity_id", "entity_id"),
        Index("ix_prov_attribute_activity_id", "activity_id"),
        Index("ix_prov_attribute_agent_id", "agent_id"),
        Index("ix_prov_attribute_attr_key", "attr_key"),
    )

    prov_attribute_id: Mapped[UUID] = mapped_column(UUID_T, primary_key=True)
    entity_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_entity')}.entity_id",
            name="fk_prov_attribute_entity_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    activity_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_activity')}.activity_id",
            name="fk_prov_attribute_activity_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    agent_id: Mapped[UUID | None] = mapped_column(
        UUID_T,
        ForeignKey(
            f"{_pc('prov_agent')}.agent_id",
            name="fk_prov_attribute_agent_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
    )
    attr_key: Mapped[str] = mapped_column(String(128), nullable=False)
    attr_value: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
