"""Mappers between domain dataclasses and SQLAlchemy models.

We keep the domain ignorant of the ORM and translate at the boundary.
"""

from __future__ import annotations

from typing import Any

from provenance_service.domain.audit.entities import (
    AuditEvent,
    BlockchainAnchor,
    HashRecord,
    OutboxEvent,
)
from provenance_service.domain.calculation.entities import (
    CalculationExecution,
    CalculationMethod,
    CalculationMethodVersion,
    CalculationParameterSet,
    CalculationParameterValue,
    CalculationResultAggregationLink,
    CalculationResultItem,
    CalculationResultSet,
    CalculationReview,
    ResultPublicationExecution,
)
from provenance_service.domain.pipeline.entities import (
    NormalizedBatch,
    PipelineRun,
    SourceArtifact,
    SourceArtifactRevision,
    WrapperDefinition,
    WrapperExecution,
)
from provenance_service.domain.prov_core.entities import (
    ProvActivity,
    ProvAgent,
    ProvAttribute,
    ProvBundle,
    ProvEntity,
)
from provenance_service.domain.prov_core.relations import (
    ProvAssociatedWith,
    ProvDerivedFrom,
    ProvGenerated,
    ProvRevision,
    ProvUsed,
)
from provenance_service.domain.reporting.entities import ReportingPeriod
from provenance_service.domain.semantic.entities import (
    CanonicalSnapshot,
    CanonicalSnapshotItem,
    OntologyResourceLink,
    SemanticIntegrationExecution,
)
from provenance_service.infrastructure.db.models import audit as audit_models
from provenance_service.infrastructure.db.models import calculation as calc_models
from provenance_service.infrastructure.db.models import pipeline as pipe_models
from provenance_service.infrastructure.db.models import prov_core as prov_models
from provenance_service.infrastructure.db.models import reporting as rep_models
from provenance_service.infrastructure.db.models import semantic as sem_models


def _md(value: Any) -> dict[str, Any]:
    return dict(value) if value is not None else {}


# ---------- pipeline ----------


def to_pipeline_run_model(d: PipelineRun) -> pipe_models.PipelineRunModel:
    return pipe_models.PipelineRunModel(
        pipeline_run_id=d.pipeline_run_id,
        run_code=d.run_code,
        tenant_id=d.tenant_id,
        farm_reference=d.farm_reference,
        reporting_period_reference=d.reporting_period_reference,
        run_status=d.run_status.value,
        started_at=d.started_at,
        finished_at=d.finished_at,
        parent_pipeline_run_id=d.parent_pipeline_run_id,
        triggered_by_agent_id=d.triggered_by_agent_id,
        notes=d.notes,
        idempotency_key=d.idempotency_key,
        run_type=d.run_type.value if d.run_type is not None else None,
        reporting_period_id=d.reporting_period_id,
        farm_id_hash=d.farm_id_hash,
        project_id_hash=d.project_id_hash,
        extra_metadata=dict(d.metadata),
    )


def from_pipeline_run_model(m: pipe_models.PipelineRunModel) -> PipelineRun:
    from provenance_service.domain.shared.enums import PipelineRunStatus, RunType

    return PipelineRun(
        pipeline_run_id=m.pipeline_run_id,
        run_code=m.run_code,
        tenant_id=m.tenant_id,
        farm_reference=m.farm_reference,
        reporting_period_reference=m.reporting_period_reference,
        run_status=PipelineRunStatus(m.run_status),
        started_at=m.started_at,
        finished_at=m.finished_at,
        parent_pipeline_run_id=m.parent_pipeline_run_id,
        triggered_by_agent_id=m.triggered_by_agent_id,
        notes=m.notes,
        idempotency_key=m.idempotency_key,
        run_type=RunType(m.run_type) if m.run_type else None,
        reporting_period_id=m.reporting_period_id,
        farm_id_hash=m.farm_id_hash,
        project_id_hash=m.project_id_hash,
        metadata=_md(m.extra_metadata),
    )


def to_source_artifact_model(d: SourceArtifact) -> pipe_models.SourceArtifactModel:
    return pipe_models.SourceArtifactModel(
        source_artifact_id=d.source_artifact_id,
        pipeline_run_id=d.pipeline_run_id,
        prov_entity_id=d.prov_entity_id,
        source_system=d.source_system,
        source_layout_name=d.source_layout_name,
        source_layout_version=d.source_layout_version,
        original_filename=d.original_filename,
        storage_uri=d.storage_uri,
        mime_type=d.mime_type,
        file_size_bytes=d.file_size_bytes,
        content_hash=d.content_hash,
        received_at=d.received_at,
        idempotency_key=d.idempotency_key,
        extra_metadata=dict(d.metadata),
    )


def from_source_artifact_model(m: pipe_models.SourceArtifactModel) -> SourceArtifact:
    return SourceArtifact(
        source_artifact_id=m.source_artifact_id,
        pipeline_run_id=m.pipeline_run_id,
        prov_entity_id=m.prov_entity_id,
        source_system=m.source_system,
        source_layout_name=m.source_layout_name,
        source_layout_version=m.source_layout_version,
        original_filename=m.original_filename,
        storage_uri=m.storage_uri,
        mime_type=m.mime_type,
        file_size_bytes=m.file_size_bytes,
        content_hash=m.content_hash,
        received_at=m.received_at,
        idempotency_key=m.idempotency_key,
        metadata=_md(m.extra_metadata),
    )


def to_source_artifact_revision_model(
    d: SourceArtifactRevision,
) -> pipe_models.SourceArtifactRevisionModel:
    return pipe_models.SourceArtifactRevisionModel(
        source_artifact_revision_id=d.source_artifact_revision_id,
        source_artifact_id=d.source_artifact_id,
        revision_number=d.revision_number,
        storage_uri=d.storage_uri,
        content_hash=d.content_hash,
        mime_type=d.mime_type,
        file_size_bytes=d.file_size_bytes,
        received_at=d.received_at,
        is_current=d.is_current,
        prov_entity_id=d.prov_entity_id,
        extra_metadata=dict(d.metadata),
    )


def from_source_artifact_revision_model(
    m: pipe_models.SourceArtifactRevisionModel,
) -> SourceArtifactRevision:
    return SourceArtifactRevision(
        source_artifact_revision_id=m.source_artifact_revision_id,
        source_artifact_id=m.source_artifact_id,
        revision_number=m.revision_number,
        storage_uri=m.storage_uri,
        content_hash=m.content_hash,
        mime_type=m.mime_type,
        file_size_bytes=m.file_size_bytes,
        received_at=m.received_at,
        is_current=m.is_current,
        prov_entity_id=m.prov_entity_id,
        metadata=_md(m.extra_metadata),
    )


def to_wrapper_definition_model(
    d: WrapperDefinition,
) -> pipe_models.WrapperDefinitionModel:
    return pipe_models.WrapperDefinitionModel(
        wrapper_definition_id=d.wrapper_definition_id,
        wrapper_name=d.wrapper_name,
        wrapper_version=d.wrapper_version,
        source_layout_name=d.source_layout_name,
        source_layout_version=d.source_layout_version,
        schema_version=d.schema_version,
        code_hash=d.code_hash,
        wrapper_code_hash=d.wrapper_code_hash,
        input_schema_hash=d.input_schema_hash,
        output_schema_hash=d.output_schema_hash,
        is_active=d.is_active,
        created_at=d.created_at,
        extra_metadata=dict(d.metadata),
    )


def from_wrapper_definition_model(
    m: pipe_models.WrapperDefinitionModel,
) -> WrapperDefinition:
    return WrapperDefinition(
        wrapper_definition_id=m.wrapper_definition_id,
        wrapper_name=m.wrapper_name,
        wrapper_version=m.wrapper_version,
        source_layout_name=m.source_layout_name,
        source_layout_version=m.source_layout_version,
        schema_version=m.schema_version,
        code_hash=m.code_hash,
        wrapper_code_hash=m.wrapper_code_hash,
        input_schema_hash=m.input_schema_hash,
        output_schema_hash=m.output_schema_hash,
        is_active=m.is_active,
        created_at=m.created_at,
        metadata=_md(m.extra_metadata),
    )


def to_wrapper_execution_model(
    d: WrapperExecution,
) -> pipe_models.WrapperExecutionModel:
    return pipe_models.WrapperExecutionModel(
        wrapper_execution_id=d.wrapper_execution_id,
        pipeline_run_id=d.pipeline_run_id,
        prov_activity_id=d.prov_activity_id,
        wrapper_definition_id=d.wrapper_definition_id,
        input_artifact_id=d.input_artifact_id,
        input_source_artifact_revision_id=d.input_source_artifact_revision_id,
        execution_status=d.execution_status.value,
        started_at=d.started_at,
        finished_at=d.finished_at,
        warning_count=d.warning_count,
        error_count=d.error_count,
        execution_log_uri=d.execution_log_uri,
        idempotency_key=d.idempotency_key,
        execution_payload_hash=d.execution_payload_hash,
        runtime_version=d.runtime_version,
        extra_metadata=dict(d.metadata),
    )


def from_wrapper_execution_model(
    m: pipe_models.WrapperExecutionModel,
) -> WrapperExecution:
    from provenance_service.domain.shared.enums import WrapperExecutionStatus

    return WrapperExecution(
        wrapper_execution_id=m.wrapper_execution_id,
        pipeline_run_id=m.pipeline_run_id,
        prov_activity_id=m.prov_activity_id,
        wrapper_definition_id=m.wrapper_definition_id,
        input_artifact_id=m.input_artifact_id,
        execution_status=WrapperExecutionStatus(m.execution_status),
        started_at=m.started_at,
        finished_at=m.finished_at,
        warning_count=m.warning_count,
        error_count=m.error_count,
        execution_log_uri=m.execution_log_uri,
        idempotency_key=m.idempotency_key,
        input_source_artifact_revision_id=m.input_source_artifact_revision_id,
        execution_payload_hash=m.execution_payload_hash,
        runtime_version=m.runtime_version,
        metadata=_md(m.extra_metadata),
    )


def to_normalized_batch_model(d: NormalizedBatch) -> pipe_models.NormalizedBatchModel:
    return pipe_models.NormalizedBatchModel(
        normalized_batch_id=d.normalized_batch_id,
        pipeline_run_id=d.pipeline_run_id,
        prov_entity_id=d.prov_entity_id,
        wrapper_execution_id=d.wrapper_execution_id,
        batch_code=d.batch_code,
        schema_version=d.schema_version,
        record_count=d.record_count,
        storage_uri=d.storage_uri,
        content_hash=d.content_hash,
        generated_at=d.generated_at,
        idempotency_key=d.idempotency_key,
        extra_metadata=dict(d.metadata),
    )


def from_normalized_batch_model(m: pipe_models.NormalizedBatchModel) -> NormalizedBatch:
    return NormalizedBatch(
        normalized_batch_id=m.normalized_batch_id,
        pipeline_run_id=m.pipeline_run_id,
        prov_entity_id=m.prov_entity_id,
        wrapper_execution_id=m.wrapper_execution_id,
        batch_code=m.batch_code,
        schema_version=m.schema_version,
        record_count=m.record_count,
        storage_uri=m.storage_uri,
        content_hash=m.content_hash,
        generated_at=m.generated_at,
        idempotency_key=m.idempotency_key,
        metadata=_md(m.extra_metadata),
    )


# ---------- prov_core ----------


def to_prov_bundle_model(d: ProvBundle) -> prov_models.ProvBundleModel:
    return prov_models.ProvBundleModel(
        bundle_id=d.bundle_id,
        pipeline_run_id=d.pipeline_run_id,
        bundle_type=d.bundle_type.value,
        name=d.name,
        status=d.status.value,
        created_at=d.created_at,
        closed_at=d.closed_at,
        extra_metadata=dict(d.metadata),
    )


def from_prov_bundle_model(m: prov_models.ProvBundleModel) -> ProvBundle:
    from provenance_service.domain.shared.enums import ProvBundleStatus, ProvBundleType

    return ProvBundle(
        bundle_id=m.bundle_id,
        pipeline_run_id=m.pipeline_run_id,
        bundle_type=ProvBundleType(m.bundle_type),
        name=m.name,
        status=ProvBundleStatus(m.status),
        created_at=m.created_at,
        closed_at=m.closed_at,
        metadata=_md(m.extra_metadata),
    )


def to_prov_entity_model(d: ProvEntity) -> prov_models.ProvEntityModel:
    return prov_models.ProvEntityModel(
        entity_id=d.entity_id,
        bundle_id=d.bundle_id,
        pipeline_run_id=d.pipeline_run_id,
        entity_type=d.entity_type.value,
        entity_kind=d.entity_kind,
        entity_ref_id=d.entity_ref_id,
        business_key=d.business_key,
        name=d.name,
        description=d.description,
        version_label=d.version_label,
        content_hash=d.content_hash,
        created_at=d.created_at,
        invalidated_at=d.invalidated_at,
        extra_metadata=dict(d.metadata),
    )


def from_prov_entity_model(m: prov_models.ProvEntityModel) -> ProvEntity:
    from provenance_service.domain.shared.enums import ProvEntityType

    return ProvEntity(
        entity_id=m.entity_id,
        bundle_id=m.bundle_id,
        pipeline_run_id=m.pipeline_run_id,
        entity_type=ProvEntityType(m.entity_type),
        entity_kind=m.entity_kind,
        entity_ref_id=m.entity_ref_id,
        business_key=m.business_key,
        name=m.name,
        description=m.description,
        version_label=m.version_label,
        content_hash=m.content_hash,
        created_at=m.created_at,
        invalidated_at=m.invalidated_at,
        metadata=_md(m.extra_metadata),
    )


def to_prov_activity_model(d: ProvActivity) -> prov_models.ProvActivityModel:
    return prov_models.ProvActivityModel(
        activity_id=d.activity_id,
        bundle_id=d.bundle_id,
        pipeline_run_id=d.pipeline_run_id,
        activity_type=d.activity_type.value,
        business_key=d.business_key,
        name=d.name,
        status=d.status,
        started_at=d.started_at,
        ended_at=d.ended_at,
        software_version=d.software_version,
        recorded_at=d.recorded_at,
        extra_metadata=dict(d.metadata),
    )


def from_prov_activity_model(m: prov_models.ProvActivityModel) -> ProvActivity:
    from provenance_service.domain.shared.enums import ProvActivityType

    return ProvActivity(
        activity_id=m.activity_id,
        bundle_id=m.bundle_id,
        pipeline_run_id=m.pipeline_run_id,
        activity_type=ProvActivityType(m.activity_type),
        business_key=m.business_key,
        name=m.name,
        status=m.status,
        started_at=m.started_at,
        ended_at=m.ended_at,
        software_version=m.software_version,
        recorded_at=m.recorded_at,
        metadata=_md(m.extra_metadata),
    )


def to_prov_agent_model(d: ProvAgent) -> prov_models.ProvAgentModel:
    return prov_models.ProvAgentModel(
        agent_id=d.agent_id,
        agent_type=d.agent_type.value,
        name=d.name,
        external_reference=d.external_reference,
        organization_name=d.organization_name,
        created_at=d.created_at,
        extra_metadata=dict(d.metadata),
    )


def from_prov_agent_model(m: prov_models.ProvAgentModel) -> ProvAgent:
    from provenance_service.domain.shared.enums import ProvAgentType

    return ProvAgent(
        agent_id=m.agent_id,
        agent_type=ProvAgentType(m.agent_type),
        name=m.name,
        external_reference=m.external_reference,
        organization_name=m.organization_name,
        created_at=m.created_at,
        metadata=_md(m.extra_metadata),
    )


def to_prov_used_model(d: ProvUsed) -> prov_models.ProvUsedModel:
    return prov_models.ProvUsedModel(
        used_id=d.used_id,
        activity_id=d.activity_id,
        entity_id=d.entity_id,
        role=d.role,
        used_at=d.used_at,
        extra_metadata=dict(d.metadata),
    )


def from_prov_used_model(m: prov_models.ProvUsedModel) -> ProvUsed:
    return ProvUsed(
        used_id=m.used_id,
        activity_id=m.activity_id,
        entity_id=m.entity_id,
        role=m.role,
        used_at=m.used_at,
        metadata=_md(m.extra_metadata),
    )


def to_prov_generated_model(d: ProvGenerated) -> prov_models.ProvGeneratedModel:
    return prov_models.ProvGeneratedModel(
        generated_id=d.generated_id,
        entity_id=d.entity_id,
        activity_id=d.activity_id,
        generated_at=d.generated_at,
        extra_metadata=dict(d.metadata),
    )


def from_prov_generated_model(m: prov_models.ProvGeneratedModel) -> ProvGenerated:
    return ProvGenerated(
        generated_id=m.generated_id,
        entity_id=m.entity_id,
        activity_id=m.activity_id,
        generated_at=m.generated_at,
        metadata=_md(m.extra_metadata),
    )


def to_prov_derived_from_model(
    d: ProvDerivedFrom,
) -> prov_models.ProvDerivedFromModel:
    return prov_models.ProvDerivedFromModel(
        derived_id=d.derived_id,
        generated_entity_id=d.generated_entity_id,
        source_entity_id=d.source_entity_id,
        derivation_type=d.derivation_type,
        extra_metadata=dict(d.metadata),
    )


def from_prov_derived_from_model(
    m: prov_models.ProvDerivedFromModel,
) -> ProvDerivedFrom:
    return ProvDerivedFrom(
        derived_id=m.derived_id,
        generated_entity_id=m.generated_entity_id,
        source_entity_id=m.source_entity_id,
        derivation_type=m.derivation_type,
        metadata=_md(m.extra_metadata),
    )


def to_prov_associated_with_model(
    d: ProvAssociatedWith,
) -> prov_models.ProvAssociatedWithModel:
    return prov_models.ProvAssociatedWithModel(
        association_id=d.association_id,
        activity_id=d.activity_id,
        agent_id=d.agent_id,
        role=d.role,
        extra_metadata=dict(d.metadata),
    )


def from_prov_associated_with_model(
    m: prov_models.ProvAssociatedWithModel,
) -> ProvAssociatedWith:
    return ProvAssociatedWith(
        association_id=m.association_id,
        activity_id=m.activity_id,
        agent_id=m.agent_id,
        role=m.role,
        metadata=_md(m.extra_metadata),
    )


def to_prov_revision_model(d: ProvRevision) -> prov_models.ProvRevisionModel:
    return prov_models.ProvRevisionModel(
        revision_id=d.revision_id,
        previous_entity_id=d.previous_entity_id,
        new_entity_id=d.new_entity_id,
        revision_reason=d.revision_reason,
        revised_at=d.revised_at,
        extra_metadata=dict(d.metadata),
    )


def from_prov_revision_model(m: prov_models.ProvRevisionModel) -> ProvRevision:
    return ProvRevision(
        revision_id=m.revision_id,
        previous_entity_id=m.previous_entity_id,
        new_entity_id=m.new_entity_id,
        revision_reason=m.revision_reason,
        revised_at=m.revised_at,
        metadata=_md(m.extra_metadata),
    )


def to_prov_attribute_model(d: ProvAttribute) -> prov_models.ProvAttributeModel:
    return prov_models.ProvAttributeModel(
        prov_attribute_id=d.prov_attribute_id,
        entity_id=d.entity_id,
        activity_id=d.activity_id,
        agent_id=d.agent_id,
        attr_key=d.attr_key,
        attr_value=dict(d.attr_value),
        recorded_at=d.recorded_at,
    )


def from_prov_attribute_model(m: prov_models.ProvAttributeModel) -> ProvAttribute:
    return ProvAttribute(
        prov_attribute_id=m.prov_attribute_id,
        entity_id=m.entity_id,
        activity_id=m.activity_id,
        agent_id=m.agent_id,
        attr_key=m.attr_key,
        attr_value=dict(m.attr_value),
        recorded_at=m.recorded_at,
    )


# ---------- semantic ----------


def to_semantic_integration_execution_model(
    d: SemanticIntegrationExecution,
) -> sem_models.SemanticIntegrationExecutionModel:
    return sem_models.SemanticIntegrationExecutionModel(
        semantic_integration_execution_id=d.semantic_integration_execution_id,
        pipeline_run_id=d.pipeline_run_id,
        prov_activity_id=d.prov_activity_id,
        normalized_batch_id=d.normalized_batch_id,
        ontology_name=d.ontology_name,
        ontology_version=d.ontology_version,
        mapping_rule_version=d.mapping_rule_version,
        execution_status=d.execution_status.value,
        started_at=d.started_at,
        finished_at=d.finished_at,
        triples_generated=d.triples_generated,
        idempotency_key=d.idempotency_key,
        extra_metadata=dict(d.metadata),
    )


def from_semantic_integration_execution_model(
    m: sem_models.SemanticIntegrationExecutionModel,
) -> SemanticIntegrationExecution:
    from provenance_service.domain.shared.enums import SemanticExecutionStatus

    return SemanticIntegrationExecution(
        semantic_integration_execution_id=m.semantic_integration_execution_id,
        pipeline_run_id=m.pipeline_run_id,
        prov_activity_id=m.prov_activity_id,
        normalized_batch_id=m.normalized_batch_id,
        ontology_name=m.ontology_name,
        ontology_version=m.ontology_version,
        mapping_rule_version=m.mapping_rule_version,
        execution_status=SemanticExecutionStatus(m.execution_status),
        started_at=m.started_at,
        finished_at=m.finished_at,
        triples_generated=m.triples_generated,
        idempotency_key=m.idempotency_key,
        metadata=_md(m.extra_metadata),
    )


def to_canonical_snapshot_model(
    d: CanonicalSnapshot,
) -> sem_models.CanonicalSnapshotModel:
    return sem_models.CanonicalSnapshotModel(
        canonical_snapshot_id=d.canonical_snapshot_id,
        pipeline_run_id=d.pipeline_run_id,
        prov_entity_id=d.prov_entity_id,
        semantic_integration_execution_id=d.semantic_integration_execution_id,
        graph_name=d.graph_name,
        snapshot_label=d.snapshot_label,
        snapshot_hash=d.snapshot_hash,
        schema_version=d.schema_version,
        canonical_schema_version=d.canonical_schema_version,
        item_count=d.item_count,
        snapshot_payload_ref=d.snapshot_payload_ref,
        storage_uri=d.storage_uri,
        payload=dict(d.payload) if d.payload is not None else None,
        reporting_period_id=d.reporting_period_id,
        published_at=d.published_at,
        extra_metadata=dict(d.metadata),
    )


def from_canonical_snapshot_model(
    m: sem_models.CanonicalSnapshotModel,
) -> CanonicalSnapshot:
    return CanonicalSnapshot(
        canonical_snapshot_id=m.canonical_snapshot_id,
        pipeline_run_id=m.pipeline_run_id,
        prov_entity_id=m.prov_entity_id,
        semantic_integration_execution_id=m.semantic_integration_execution_id,
        graph_name=m.graph_name,
        snapshot_label=m.snapshot_label,
        snapshot_hash=m.snapshot_hash,
        schema_version=m.schema_version,
        canonical_schema_version=m.canonical_schema_version,
        item_count=m.item_count,
        snapshot_payload_ref=m.snapshot_payload_ref,
        storage_uri=m.storage_uri,
        payload=dict(m.payload) if m.payload is not None else None,
        reporting_period_id=m.reporting_period_id,
        published_at=m.published_at,
        metadata=_md(m.extra_metadata),
    )


def to_canonical_snapshot_item_model(
    d: CanonicalSnapshotItem,
) -> sem_models.CanonicalSnapshotItemModel:
    return sem_models.CanonicalSnapshotItemModel(
        canonical_snapshot_item_id=d.canonical_snapshot_item_id,
        canonical_snapshot_id=d.canonical_snapshot_id,
        item_key=d.item_key,
        payload=dict(d.payload),
        item_hash=d.item_hash,
    )


def from_canonical_snapshot_item_model(
    m: sem_models.CanonicalSnapshotItemModel,
) -> CanonicalSnapshotItem:
    return CanonicalSnapshotItem(
        canonical_snapshot_item_id=m.canonical_snapshot_item_id,
        canonical_snapshot_id=m.canonical_snapshot_id,
        item_key=m.item_key,
        payload=dict(m.payload),
        item_hash=m.item_hash,
    )


def to_ontology_resource_link_model(
    d: OntologyResourceLink,
) -> sem_models.OntologyResourceLinkModel:
    return sem_models.OntologyResourceLinkModel(
        ontology_resource_link_id=d.ontology_resource_link_id,
        pipeline_run_id=d.pipeline_run_id,
        prov_entity_id=d.prov_entity_id,
        canonical_snapshot_id=d.canonical_snapshot_id,
        ontology_uri=d.ontology_uri,
        rdf_class=d.rdf_class,
        graph_name=d.graph_name,
        ontology_version=d.ontology_version,
        publication_stage=d.publication_stage.value,
        published_at=d.published_at,
        extra_metadata=dict(d.metadata),
    )


def from_ontology_resource_link_model(
    m: sem_models.OntologyResourceLinkModel,
) -> OntologyResourceLink:
    from provenance_service.domain.shared.enums import PublicationStage

    return OntologyResourceLink(
        ontology_resource_link_id=m.ontology_resource_link_id,
        pipeline_run_id=m.pipeline_run_id,
        prov_entity_id=m.prov_entity_id,
        canonical_snapshot_id=m.canonical_snapshot_id,
        ontology_uri=m.ontology_uri,
        rdf_class=m.rdf_class,
        graph_name=m.graph_name,
        ontology_version=m.ontology_version,
        publication_stage=PublicationStage(m.publication_stage),
        published_at=m.published_at,
        metadata=_md(m.extra_metadata),
    )


# ---------- calculation ----------


def to_calculation_method_model(d: CalculationMethod) -> calc_models.CalculationMethodModel:
    return calc_models.CalculationMethodModel(
        calculation_method_id=d.calculation_method_id,
        method_code=d.method_code,
        method_name=d.method_name,
        description=d.description,
        created_at=d.created_at,
    )


def from_calculation_method_model(m: calc_models.CalculationMethodModel) -> CalculationMethod:
    return CalculationMethod(
        calculation_method_id=m.calculation_method_id,
        method_code=m.method_code,
        method_name=m.method_name,
        description=m.description,
        created_at=m.created_at,
    )


def to_calculation_method_version_model(
    d: CalculationMethodVersion,
) -> calc_models.CalculationMethodVersionModel:
    return calc_models.CalculationMethodVersionModel(
        calculation_method_version_id=d.calculation_method_version_id,
        calculation_method_id=d.calculation_method_id,
        version_label=d.version_label,
        formula_reference=d.formula_reference,
        formula_hash=d.formula_hash,
        method_document_uri=d.method_document_uri,
        method_document_hash=d.method_document_hash,
        implementation_version=d.implementation_version,
        effective_from=d.effective_from,
        effective_to=d.effective_to,
        status=d.status.value,
        extra_metadata=dict(d.metadata),
    )


def from_calculation_method_version_model(
    m: calc_models.CalculationMethodVersionModel,
) -> CalculationMethodVersion:
    from provenance_service.domain.shared.enums import CalculationMethodStatus

    return CalculationMethodVersion(
        calculation_method_version_id=m.calculation_method_version_id,
        calculation_method_id=m.calculation_method_id,
        version_label=m.version_label,
        formula_reference=m.formula_reference,
        formula_hash=m.formula_hash,
        method_document_uri=m.method_document_uri,
        method_document_hash=m.method_document_hash,
        implementation_version=m.implementation_version,
        effective_from=m.effective_from,
        effective_to=m.effective_to,
        status=CalculationMethodStatus(m.status),
        metadata=_md(m.extra_metadata),
    )


def to_calculation_parameter_set_model(
    d: CalculationParameterSet,
) -> calc_models.CalculationParameterSetModel:
    return calc_models.CalculationParameterSetModel(
        calculation_parameter_set_id=d.calculation_parameter_set_id,
        pipeline_run_id=d.pipeline_run_id,
        prov_entity_id=d.prov_entity_id,
        calculation_method_version_id=d.calculation_method_version_id,
        parameter_set_status=d.parameter_set_status.value,
        created_by_agent_id=d.created_by_agent_id,
        created_at=d.created_at,
        notes=d.notes,
        extra_metadata=dict(d.metadata),
    )


def from_calculation_parameter_set_model(
    m: calc_models.CalculationParameterSetModel,
) -> CalculationParameterSet:
    from provenance_service.domain.shared.enums import ParameterSetStatus

    return CalculationParameterSet(
        calculation_parameter_set_id=m.calculation_parameter_set_id,
        pipeline_run_id=m.pipeline_run_id,
        prov_entity_id=m.prov_entity_id,
        calculation_method_version_id=m.calculation_method_version_id,
        parameter_set_status=ParameterSetStatus(m.parameter_set_status),
        created_by_agent_id=m.created_by_agent_id,
        created_at=m.created_at,
        notes=m.notes,
        metadata=_md(m.extra_metadata),
    )


def to_calculation_parameter_value_model(
    d: CalculationParameterValue,
) -> calc_models.CalculationParameterValueModel:
    return calc_models.CalculationParameterValueModel(
        calculation_parameter_value_id=d.calculation_parameter_value_id,
        calculation_parameter_set_id=d.calculation_parameter_set_id,
        parameter_name=d.parameter_name,
        parameter_value_text=d.parameter_value_text,
        parameter_value_numeric=d.parameter_value_numeric,
        parameter_unit=d.parameter_unit,
        parameter_source=d.parameter_source,
        is_user_editable=d.is_user_editable,
        extra_metadata=dict(d.metadata),
    )


def from_calculation_parameter_value_model(
    m: calc_models.CalculationParameterValueModel,
) -> CalculationParameterValue:
    return CalculationParameterValue(
        calculation_parameter_value_id=m.calculation_parameter_value_id,
        calculation_parameter_set_id=m.calculation_parameter_set_id,
        parameter_name=m.parameter_name,
        parameter_value_text=m.parameter_value_text,
        parameter_value_numeric=m.parameter_value_numeric,
        parameter_unit=m.parameter_unit,
        parameter_source=m.parameter_source,
        is_user_editable=m.is_user_editable,
        metadata=_md(m.extra_metadata),
    )


def to_calculation_execution_model(
    d: CalculationExecution,
) -> calc_models.CalculationExecutionModel:
    return calc_models.CalculationExecutionModel(
        calculation_execution_id=d.calculation_execution_id,
        pipeline_run_id=d.pipeline_run_id,
        prov_activity_id=d.prov_activity_id,
        canonical_snapshot_id=d.canonical_snapshot_id,
        calculation_method_version_id=d.calculation_method_version_id,
        calculation_parameter_set_id=d.calculation_parameter_set_id,
        execution_status=d.execution_status.value,
        started_at=d.started_at,
        finished_at=d.finished_at,
        execution_log_uri=d.execution_log_uri,
        idempotency_key=d.idempotency_key,
        reporting_period_id=d.reporting_period_id,
        extra_metadata=dict(d.metadata),
    )


def from_calculation_execution_model(
    m: calc_models.CalculationExecutionModel,
) -> CalculationExecution:
    from provenance_service.domain.shared.enums import CalculationExecutionStatus

    return CalculationExecution(
        calculation_execution_id=m.calculation_execution_id,
        pipeline_run_id=m.pipeline_run_id,
        prov_activity_id=m.prov_activity_id,
        canonical_snapshot_id=m.canonical_snapshot_id,
        calculation_method_version_id=m.calculation_method_version_id,
        calculation_parameter_set_id=m.calculation_parameter_set_id,
        execution_status=CalculationExecutionStatus(m.execution_status),
        started_at=m.started_at,
        finished_at=m.finished_at,
        execution_log_uri=m.execution_log_uri,
        idempotency_key=m.idempotency_key,
        reporting_period_id=m.reporting_period_id,
        metadata=_md(m.extra_metadata),
    )


def to_calculation_result_set_model(
    d: CalculationResultSet,
) -> calc_models.CalculationResultSetModel:
    return calc_models.CalculationResultSetModel(
        calculation_result_set_id=d.calculation_result_set_id,
        pipeline_run_id=d.pipeline_run_id,
        prov_entity_id=d.prov_entity_id,
        calculation_execution_id=d.calculation_execution_id,
        result_set_status=d.result_set_status.value,
        generated_at=d.generated_at,
        summary_hash=d.summary_hash,
        superseded_by_id=d.superseded_by_id,
        reporting_period_id=d.reporting_period_id,
        result_scope=d.result_scope.value if d.result_scope is not None else None,
        consolidation_type=(
            d.consolidation_type.value if d.consolidation_type is not None else None
        ),
        approved_at=d.approved_at,
        published_at=d.published_at,
        supersedes_id=d.supersedes_id,
        correction_reason=d.correction_reason,
        extra_metadata=dict(d.metadata),
    )


def from_calculation_result_set_model(
    m: calc_models.CalculationResultSetModel,
) -> CalculationResultSet:
    from provenance_service.domain.shared.enums import (
        CalculationResultSetStatus,
        ConsolidationType,
        ResultScope,
    )

    return CalculationResultSet(
        calculation_result_set_id=m.calculation_result_set_id,
        pipeline_run_id=m.pipeline_run_id,
        prov_entity_id=m.prov_entity_id,
        calculation_execution_id=m.calculation_execution_id,
        result_set_status=CalculationResultSetStatus(m.result_set_status),
        generated_at=m.generated_at,
        summary_hash=m.summary_hash,
        superseded_by_id=m.superseded_by_id,
        reporting_period_id=m.reporting_period_id,
        result_scope=ResultScope(m.result_scope) if m.result_scope else None,
        consolidation_type=(
            ConsolidationType(m.consolidation_type) if m.consolidation_type else None
        ),
        approved_at=m.approved_at,
        published_at=m.published_at,
        supersedes_id=m.supersedes_id,
        correction_reason=m.correction_reason,
        metadata=_md(m.extra_metadata),
    )


def to_calculation_result_item_model(
    d: CalculationResultItem,
) -> calc_models.CalculationResultItemModel:
    return calc_models.CalculationResultItemModel(
        calculation_result_item_id=d.calculation_result_item_id,
        calculation_result_set_id=d.calculation_result_set_id,
        result_type=d.result_type.value,
        result_name=d.result_name,
        result_value=d.result_value,
        result_unit=d.result_unit,
        dimension_reference=d.dimension_reference,
        extra_metadata=dict(d.metadata),
    )


def from_calculation_result_item_model(
    m: calc_models.CalculationResultItemModel,
) -> CalculationResultItem:
    from provenance_service.domain.shared.enums import CalculationResultType

    return CalculationResultItem(
        calculation_result_item_id=m.calculation_result_item_id,
        calculation_result_set_id=m.calculation_result_set_id,
        result_type=CalculationResultType(m.result_type),
        result_name=m.result_name,
        result_value=m.result_value,
        result_unit=m.result_unit,
        dimension_reference=m.dimension_reference,
        metadata=_md(m.extra_metadata),
    )


def to_calculation_review_model(d: CalculationReview) -> calc_models.CalculationReviewModel:
    return calc_models.CalculationReviewModel(
        calculation_review_id=d.calculation_review_id,
        pipeline_run_id=d.pipeline_run_id,
        prov_activity_id=d.prov_activity_id,
        calculation_result_set_id=d.calculation_result_set_id,
        reviewer_agent_id=d.reviewer_agent_id,
        decision=d.decision.value,
        review_comment=d.review_comment,
        reviewed_at=d.reviewed_at,
        evidence_uri=d.evidence_uri,
        reporting_period_id=d.reporting_period_id,
        extra_metadata=dict(d.metadata),
    )


def from_calculation_review_model(m: calc_models.CalculationReviewModel) -> CalculationReview:
    from provenance_service.domain.shared.enums import CalculationReviewDecision

    return CalculationReview(
        calculation_review_id=m.calculation_review_id,
        pipeline_run_id=m.pipeline_run_id,
        prov_activity_id=m.prov_activity_id,
        calculation_result_set_id=m.calculation_result_set_id,
        reviewer_agent_id=m.reviewer_agent_id,
        decision=CalculationReviewDecision(m.decision),
        review_comment=m.review_comment,
        reviewed_at=m.reviewed_at,
        evidence_uri=m.evidence_uri,
        reporting_period_id=m.reporting_period_id,
        metadata=_md(m.extra_metadata),
    )


def to_result_publication_execution_model(
    d: ResultPublicationExecution,
) -> calc_models.ResultPublicationExecutionModel:
    return calc_models.ResultPublicationExecutionModel(
        result_publication_execution_id=d.result_publication_execution_id,
        pipeline_run_id=d.pipeline_run_id,
        prov_activity_id=d.prov_activity_id,
        calculation_result_set_id=d.calculation_result_set_id,
        calculation_review_id=d.calculation_review_id,
        target_graph_name=d.target_graph_name,
        ontology_name=d.ontology_name,
        ontology_version=d.ontology_version,
        publication_status=d.publication_status.value,
        published_at=d.published_at,
        reporting_period_id=d.reporting_period_id,
        publication_payload_hash=d.publication_payload_hash,
        ontology_resource_uri=d.ontology_resource_uri,
        publication_version=d.publication_version,
        extra_metadata=dict(d.metadata),
    )


def from_result_publication_execution_model(
    m: calc_models.ResultPublicationExecutionModel,
) -> ResultPublicationExecution:
    from provenance_service.domain.shared.enums import ResultPublicationStatus

    return ResultPublicationExecution(
        result_publication_execution_id=m.result_publication_execution_id,
        pipeline_run_id=m.pipeline_run_id,
        prov_activity_id=m.prov_activity_id,
        calculation_result_set_id=m.calculation_result_set_id,
        calculation_review_id=m.calculation_review_id,
        target_graph_name=m.target_graph_name,
        ontology_name=m.ontology_name,
        ontology_version=m.ontology_version,
        publication_status=ResultPublicationStatus(m.publication_status),
        published_at=m.published_at,
        reporting_period_id=m.reporting_period_id,
        publication_payload_hash=m.publication_payload_hash,
        ontology_resource_uri=m.ontology_resource_uri,
        publication_version=m.publication_version,
        metadata=_md(m.extra_metadata),
    )


def to_calculation_result_aggregation_link_model(
    d: CalculationResultAggregationLink,
) -> calc_models.CalculationResultAggregationLinkModel:
    return calc_models.CalculationResultAggregationLinkModel(
        calculation_result_aggregation_link_id=d.calculation_result_aggregation_link_id,
        parent_result_set_id=d.parent_result_set_id,
        child_result_set_id=d.child_result_set_id,
        aggregation_type=d.aggregation_type,
        parent_period_id=d.parent_period_id,
        child_period_id=d.child_period_id,
        created_at=d.created_at,
        metadata_json=dict(d.metadata),
    )


def from_calculation_result_aggregation_link_model(
    m: calc_models.CalculationResultAggregationLinkModel,
) -> CalculationResultAggregationLink:
    return CalculationResultAggregationLink(
        calculation_result_aggregation_link_id=m.calculation_result_aggregation_link_id,
        parent_result_set_id=m.parent_result_set_id,
        child_result_set_id=m.child_result_set_id,
        aggregation_type=m.aggregation_type,
        parent_period_id=m.parent_period_id,
        child_period_id=m.child_period_id,
        created_at=m.created_at,
        metadata=dict(m.metadata_json),
    )


# ---------- reporting ----------


def to_reporting_period_model(d: ReportingPeriod) -> rep_models.ReportingPeriodModel:
    return rep_models.ReportingPeriodModel(
        reporting_period_id=d.reporting_period_id,
        period_start=d.period_start,
        period_end=d.period_end,
        period_granularity=d.period_granularity.value,
        year=d.year,
        month=d.month,
        day=d.day,
        period_label=d.period_label,
        status=d.status.value,
        created_at=d.created_at,
        updated_at=d.updated_at,
        extra_metadata=dict(d.metadata),
    )


def from_reporting_period_model(m: rep_models.ReportingPeriodModel) -> ReportingPeriod:
    from provenance_service.domain.shared.enums import PeriodGranularity, ReportingPeriodStatus

    return ReportingPeriod(
        reporting_period_id=m.reporting_period_id,
        period_start=m.period_start,
        period_end=m.period_end,
        period_granularity=PeriodGranularity(m.period_granularity),
        year=m.year,
        month=m.month,
        day=m.day,
        period_label=m.period_label,
        status=ReportingPeriodStatus(m.status),
        created_at=m.created_at,
        updated_at=m.updated_at,
        metadata=_md(m.extra_metadata),
    )


# ---------- audit ----------


def to_hash_record_model(d: HashRecord) -> audit_models.HashRecordModel:
    return audit_models.HashRecordModel(
        hash_record_id=d.hash_record_id,
        pipeline_run_id=d.pipeline_run_id,
        prov_entity_id=d.prov_entity_id,
        bundle_id=d.bundle_id,
        subject_kind=d.subject_kind.value,
        subject_id=d.subject_id,
        hash_algorithm=d.hash_algorithm.value,
        hash_value=d.hash_value,
        computed_at=d.computed_at,
        computed_by_version=d.computed_by_version,
        hash_scope=d.hash_scope,
        canonicalization_method=d.canonicalization_method,
        canonical_payload_hash=d.canonical_payload_hash,
        canonical_payload_ref=d.canonical_payload_ref,
        created_by_service=d.created_by_service,
        record_created_at=d.record_created_at,
        extra_metadata=dict(d.metadata),
    )


def from_hash_record_model(m: audit_models.HashRecordModel) -> HashRecord:
    from provenance_service.domain.shared.enums import HashAlgorithm, HashSubjectKind

    return HashRecord(
        hash_record_id=m.hash_record_id,
        pipeline_run_id=m.pipeline_run_id,
        prov_entity_id=m.prov_entity_id,
        bundle_id=m.bundle_id,
        subject_kind=HashSubjectKind(m.subject_kind),
        subject_id=m.subject_id,
        hash_algorithm=HashAlgorithm(m.hash_algorithm),
        hash_value=m.hash_value,
        computed_at=m.computed_at,
        computed_by_version=m.computed_by_version,
        hash_scope=m.hash_scope,
        canonicalization_method=m.canonicalization_method,
        canonical_payload_hash=m.canonical_payload_hash,
        canonical_payload_ref=m.canonical_payload_ref,
        created_by_service=m.created_by_service,
        record_created_at=m.record_created_at,
        metadata=_md(m.extra_metadata),
    )


def to_blockchain_anchor_model(d: BlockchainAnchor) -> audit_models.BlockchainAnchorModel:
    return audit_models.BlockchainAnchorModel(
        blockchain_anchor_id=d.blockchain_anchor_id,
        pipeline_run_id=d.pipeline_run_id,
        hash_record_id=d.hash_record_id,
        blockchain_network=d.blockchain_network,
        chain_id=d.chain_id,
        transaction_hash=d.transaction_hash,
        block_number=d.block_number,
        anchor_status=d.anchor_status.value,
        merkle_root=d.merkle_root,
        confirmations=d.confirmations,
        anchored_at=d.anchored_at,
        verification_uri=d.verification_uri,
        anchor_provider=d.anchor_provider,
        anchor_mode=d.anchor_mode,
        evidence_package_external_id=d.evidence_package_external_id,
        package_hash=d.package_hash,
        metadata_hash=d.metadata_hash,
        submitted_at=d.submitted_at,
        confirmed_at=d.confirmed_at,
        failed_reason=d.failed_reason,
        extra_metadata=dict(d.metadata),
    )


def from_blockchain_anchor_model(
    m: audit_models.BlockchainAnchorModel,
) -> BlockchainAnchor:
    from provenance_service.domain.shared.enums import BlockchainAnchorStatus

    return BlockchainAnchor(
        blockchain_anchor_id=m.blockchain_anchor_id,
        pipeline_run_id=m.pipeline_run_id,
        hash_record_id=m.hash_record_id,
        blockchain_network=m.blockchain_network,
        chain_id=m.chain_id,
        transaction_hash=m.transaction_hash,
        block_number=m.block_number,
        anchor_status=BlockchainAnchorStatus(m.anchor_status),
        merkle_root=m.merkle_root,
        confirmations=m.confirmations,
        anchored_at=m.anchored_at,
        verification_uri=m.verification_uri,
        anchor_provider=m.anchor_provider,
        anchor_mode=m.anchor_mode,
        evidence_package_external_id=m.evidence_package_external_id,
        package_hash=m.package_hash,
        metadata_hash=m.metadata_hash,
        submitted_at=m.submitted_at,
        confirmed_at=m.confirmed_at,
        failed_reason=m.failed_reason,
        metadata=_md(m.extra_metadata),
    )


def to_outbox_event_model(d: OutboxEvent) -> audit_models.OutboxEventModel:
    return audit_models.OutboxEventModel(
        outbox_event_id=d.outbox_event_id,
        aggregate_kind=d.aggregate_kind,
        aggregate_id=d.aggregate_id,
        event_type=d.event_type,
        payload=dict(d.payload),
        created_at=d.created_at,
        published_at=d.published_at,
        processed_at=d.processed_at,
        status=d.status.value,
        pipeline_run_id=d.pipeline_run_id,
        calculation_execution_id=d.calculation_execution_id,
        calculation_result_set_id=d.calculation_result_set_id,
        reporting_period_id=d.reporting_period_id,
        source_table=d.source_table,
        source_record_id=d.source_record_id,
        error_message=d.error_message,
        retry_count=d.retry_count,
        locked_at=d.locked_at,
        locked_by=d.locked_by,
    )


def from_outbox_event_model(m: audit_models.OutboxEventModel) -> OutboxEvent:
    from provenance_service.domain.shared.enums import OutboxStatus

    return OutboxEvent(
        outbox_event_id=m.outbox_event_id,
        aggregate_kind=m.aggregate_kind,
        aggregate_id=m.aggregate_id,
        event_type=m.event_type,
        payload=dict(m.payload),
        created_at=m.created_at,
        published_at=m.published_at,
        processed_at=m.processed_at,
        status=OutboxStatus(m.status),
        pipeline_run_id=m.pipeline_run_id,
        calculation_execution_id=m.calculation_execution_id,
        calculation_result_set_id=m.calculation_result_set_id,
        reporting_period_id=m.reporting_period_id,
        source_table=m.source_table,
        source_record_id=m.source_record_id,
        error_message=m.error_message,
        retry_count=m.retry_count,
        locked_at=m.locked_at,
        locked_by=m.locked_by,
    )


def to_audit_event_model(d: AuditEvent) -> audit_models.AuditEventModel:
    return audit_models.AuditEventModel(
        audit_event_id=d.audit_event_id,
        event_type=d.event_type,
        actor_agent_id=d.actor_agent_id,
        subject_kind=d.subject_kind,
        subject_id=d.subject_id,
        payload=dict(d.payload),
        recorded_at=d.recorded_at,
    )


def from_audit_event_model(m: audit_models.AuditEventModel) -> AuditEvent:
    return AuditEvent(
        audit_event_id=m.audit_event_id,
        event_type=m.event_type,
        actor_agent_id=m.actor_agent_id,
        subject_kind=m.subject_kind,
        subject_id=m.subject_id,
        payload=dict(m.payload),
        recorded_at=m.recorded_at,
    )
