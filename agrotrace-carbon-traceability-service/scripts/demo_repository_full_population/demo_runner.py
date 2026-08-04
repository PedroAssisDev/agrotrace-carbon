"""Shared orchestration for demo pipeline runs via ProvenanceRecorder."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from demo_config import (  # noqa: E402
    METHOD_CODE,
    ONTOLOGY_NAME,
    ONTOLOGY_VERSION,
    WRAPPER_NAME,
    WRAPPER_VERSION,
)
from demo_ids import case_id, content_hash_label, demo_id, idem_key  # noqa: E402

from provenance_service.application.services.provenance_recorder import (  # noqa: E402
    ParameterValueInput,
    ProvenanceRecorder,
    RecordBlockchainAnchorCommand,
    RecordCalculationExecutionCommand,
    RecordCalculationMethodCommand,
    RecordCalculationMethodVersionCommand,
    RecordCalculationParameterSetCommand,
    RecordCalculationResultSetCommand,
    RecordCalculationReviewCommand,
    RecordCanonicalSnapshotCommand,
    RecordHashCommand,
    RecordNormalizedBatchCommand,
    RecordOntologyResourceLinkCommand,
    RecordResultPublicationCommand,
    RecordRevisionCommand,
    RecordSemanticIntegrationCommand,
    RecordSourceArtifactCommand,
    RecordSourceArtifactRevisionCommand,
    RecordWrapperDefinitionCommand,
    RecordWrapperExecutionCommand,
    ResultItemInput,
    StartPipelineRunCommand,
)
from provenance_service.application.unit_of_work import UnitOfWork  # noqa: E402
from provenance_service.domain.audit.entities import AuditEvent  # noqa: E402
from provenance_service.domain.prov_core.entities import (  # noqa: E402
    ProvActivity,
    ProvAgent,
    ProvAttribute,
    ProvEntity,
)
from provenance_service.domain.prov_core.relations import (  # noqa: E402
    ProvDerivedFrom,
    ProvGenerated,
    ProvUsed,
)
from provenance_service.domain.shared.enums import (  # noqa: E402
    BlockchainAnchorStatus,
    CalculationResultType,
    CalculationReviewDecision,
    HashAlgorithm,
    HashSubjectKind,
    ProvActivityType,
    ProvAgentType,
    ProvBundleStatus,
    ProvBundleType,
    ProvEntityType,
    PublicationStage,
)
from provenance_service.domain.shared.ids import new_uuid7  # noqa: E402
from provenance_service.domain.shared.time import utcnow  # noqa: E402
from provenance_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork  # noqa: E402

# Populated by run_all for final summary
CREATED_SUMMARY: dict[str, Any] = {}


def log(msg: str) -> None:
    print(f"[demo] {msg}")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PipelineChainResult:
    pipeline_run_id: UUID
    run_code: str
    source_artifact_id: UUID
    source_prov_entity_id: UUID
    normalized_batch_id: UUID
    canonical_snapshot_id: UUID
    canonical_prov_entity_id: UUID
    calculation_result_set_id: UUID
    publication_execution_id: UUID | None = None
    monthly_snapshot_entity_ids: list[UUID] = field(default_factory=list)
    has_aggregation: bool = False
    aggregation_kind: str | None = None


@dataclass
class SharedCatalog:
    agent_trigger_id: UUID
    agent_reviewer_id: UUID
    agent_system_id: UUID
    calculation_method_id: UUID
    calculation_method_version_id: UUID
    wrapper_definition_id: UUID


def seed_agents_and_methods(
    uow: UnitOfWork, recorder: ProvenanceRecorder
) -> SharedCatalog:
    """Idempotent seed of agents, method and wrapper definition."""
    trigger_id = demo_id("agent", "trigger")
    reviewer_id = demo_id("agent", "reviewer")
    system_id = demo_id("agent", "system")

    for agent in (
        ProvAgent(
            agent_id=trigger_id,
            agent_type=ProvAgentType.HUMAN,
            name="Demo Trigger",
            external_reference="demo:user:trigger",
            created_at=utcnow(),
            metadata={"demo_role": "pipeline_trigger"},
        ),
        ProvAgent(
            agent_id=reviewer_id,
            agent_type=ProvAgentType.HUMAN,
            name="Demo Reviewer",
            external_reference="demo:user:reviewer",
            created_at=utcnow(),
            metadata={"demo_role": "reviewer"},
        ),
        ProvAgent(
            agent_id=system_id,
            agent_type=ProvAgentType.SOFTWARE,
            name="Demo System",
            external_reference="demo:system:aggregator",
            created_at=utcnow(),
            metadata={"demo_role": "aggregation_engine"},
        ),
    ):
        if uow.prov_agents.get(agent.agent_id) is None:
            uow.prov_agents.add(agent)

    uow.flush()

    method = recorder.record_calculation_method(
        uow,
        RecordCalculationMethodCommand(
            method_code=METHOD_CODE,
            method_name="Demo Repository GHG Method",
            calculation_method_id=demo_id("calculation_method"),
        ),
    )
    version_id = demo_id("calculation_method_version")
    version = uow.calculation_method_versions.get(version_id)
    if version is None:
        version = recorder.record_calculation_method_version(
            uow,
            RecordCalculationMethodVersionCommand(
                calculation_method_id=method.calculation_method_id,
                version_label="1.0.0",
                calculation_method_version_id=version_id,
            ),
        )

    wrapper_def = recorder.record_wrapper_definition(
        uow,
        RecordWrapperDefinitionCommand(
            wrapper_name=WRAPPER_NAME,
            wrapper_version=WRAPPER_VERSION,
            source_layout_name="demo_csv",
            wrapper_definition_id=demo_id("wrapper_definition"),
            metadata={"demo": "repository_full_population"},
        ),
    )

    return SharedCatalog(
        agent_trigger_id=trigger_id,
        agent_reviewer_id=reviewer_id,
        agent_system_id=system_id,
        calculation_method_id=method.calculation_method_id,
        calculation_method_version_id=version.calculation_method_version_id,
        wrapper_definition_id=wrapper_def.wrapper_definition_id,
    )


def _ensure_pipeline_bundle(uow: UnitOfWork, pipeline_run_id: UUID) -> UUID:
    from provenance_service.domain.prov_core.entities import ProvBundle

    bundles = uow.prov_bundles.list_by_pipeline_run(pipeline_run_id)
    for b in bundles:
        if b.bundle_type is ProvBundleType.PIPELINE_RUN:
            return b.bundle_id
    bundle_id = demo_id("bundle", str(pipeline_run_id), "pipeline_run")
    uow.prov_bundles.add(
        ProvBundle(
            bundle_id=bundle_id,
            pipeline_run_id=pipeline_run_id,
            bundle_type=ProvBundleType.PIPELINE_RUN,
            status=ProvBundleStatus.OPEN,
            created_at=utcnow(),
            name="demo-pipeline-run",
        )
    )
    uow.flush()
    return bundle_id


def run_ingestion_chain(
    uow: UnitOfWork,
    recorder: ProvenanceRecorder,
    *,
    case_key: str,
    run_code: str,
    farm_reference: str,
    reporting_period: str,
    catalog: SharedCatalog,
    milk_liters: Decimal,
    granularity: str,
    parent_pipeline_run_id: UUID | None = None,
    skip_publication: bool = False,
    extra_metadata: dict[str, Any] | None = None,
) -> PipelineChainResult:
    """Full pipeline from source artifact through calculation (optional publication)."""
    if uow.pipeline_runs.get_by_run_code(run_code) is not None:
        log(f"Skipping existing run {run_code!r}")
        existing = uow.pipeline_runs.get_by_run_code(run_code)
        assert existing is not None
        snaps = uow.canonical_snapshots.list_by_pipeline_run(existing.pipeline_run_id)
        rss = uow.calculation_result_sets.list_by_pipeline_run(existing.pipeline_run_id)
        arts = uow.source_artifacts.list_by_pipeline_run(existing.pipeline_run_id)
        batches = uow.normalized_batches.list_by_pipeline_run(existing.pipeline_run_id)
        pubs = uow.result_publication_executions.list_by_pipeline_run(existing.pipeline_run_id)
        return PipelineChainResult(
            pipeline_run_id=existing.pipeline_run_id,
            run_code=run_code,
            source_artifact_id=arts[0].source_artifact_id if arts else demo_id(case_key, "noop"),
            source_prov_entity_id=arts[0].prov_entity_id if arts else demo_id(case_key, "noop_entity"),
            normalized_batch_id=batches[0].normalized_batch_id if batches else demo_id(case_key, "noop_batch"),
            canonical_snapshot_id=snaps[0].canonical_snapshot_id if snaps else demo_id(case_key, "noop_snap"),
            canonical_prov_entity_id=snaps[0].prov_entity_id if snaps else demo_id(case_key, "noop_pe"),
            calculation_result_set_id=rss[0].calculation_result_set_id if rss else demo_id(case_key, "noop_rs"),
            publication_execution_id=pubs[0].result_publication_execution_id if pubs else None,
        )

    now = utc_now()
    meta = {
        "demo_case": case_key,
        "granularity": granularity,
        "milk_liters": str(milk_liters),
        **(extra_metadata or {}),
    }

    run = recorder.start_pipeline_run(
        uow,
        StartPipelineRunCommand(
            run_code=run_code,
            farm_reference=farm_reference,
            reporting_period_reference=reporting_period,
            triggered_by_agent_id=catalog.agent_trigger_id,
            parent_pipeline_run_id=parent_pipeline_run_id,
            idempotency_key=idem_key(case_key, "pipeline_run", run_code),
            pipeline_run_id=case_id(case_key, "pipeline_run", run_code),
            metadata=meta,
            notes=f"demo_repository_full_population:{case_key}",
        ),
    )

    ch = content_hash_label(f"{case_key}|source|{run_code}")
    artifact = recorder.record_source_artifact(
        uow,
        RecordSourceArtifactCommand(
            pipeline_run_id=run.pipeline_run_id,
            source_system="demo_repo_simulator",
            original_filename=f"{run_code}.csv",
            storage_uri=f"demo://{run_code}/raw.csv",
            content_hash=ch,
            received_at=now,
            idempotency_key=idem_key(case_key, "source_artifact", run_code),
            source_artifact_id=case_id(case_key, "source_artifact", run_code),
            prov_entity_id=case_id(case_key, "prov_entity_source", run_code),
            metadata=meta,
        ),
    )

    wrapper_ex = recorder.record_wrapper_execution(
        uow,
        RecordWrapperExecutionCommand(
            pipeline_run_id=run.pipeline_run_id,
            wrapper_definition_id=catalog.wrapper_definition_id,
            input_artifact_id=artifact.source_artifact_id,
            started_at=now,
            finished_at=now,
            idempotency_key=idem_key(case_key, "wrapper_execution", run_code),
            wrapper_execution_id=case_id(case_key, "wrapper_execution", run_code),
            prov_activity_id=case_id(case_key, "wrapper_activity", run_code),
        ),
    )

    batch_hash = content_hash_label(f"{case_key}|batch|{run_code}")
    batch = recorder.record_normalized_batch(
        uow,
        RecordNormalizedBatchCommand(
            pipeline_run_id=run.pipeline_run_id,
            wrapper_execution_id=wrapper_ex.wrapper_execution_id,
            batch_code=f"NB-{run_code}",
            schema_version="1.0",
            record_count=1,
            content_hash=batch_hash,
            generated_at=now,
            idempotency_key=idem_key(case_key, "normalized_batch", run_code),
            normalized_batch_id=case_id(case_key, "normalized_batch", run_code),
            prov_entity_id=case_id(case_key, "prov_entity_batch", run_code),
            metadata=meta,
        ),
    )

    integration = recorder.record_semantic_integration(
        uow,
        RecordSemanticIntegrationCommand(
            pipeline_run_id=run.pipeline_run_id,
            normalized_batch_id=batch.normalized_batch_id,
            ontology_name=ONTOLOGY_NAME,
            ontology_version=ONTOLOGY_VERSION,
            mapping_rule_version="1",
            started_at=now,
            finished_at=now,
            idempotency_key=idem_key(case_key, "semantic", run_code),
            semantic_integration_execution_id=case_id(case_key, "semantic", run_code),
            prov_activity_id=case_id(case_key, "semantic_activity", run_code),
        ),
    )

    payload = {
        "farm": farm_reference,
        "period": reporting_period,
        "milk_liters": str(milk_liters),
        "granularity": granularity,
    }
    snapshot = recorder.record_canonical_snapshot(
        uow,
        RecordCanonicalSnapshotCommand(
            pipeline_run_id=run.pipeline_run_id,
            semantic_integration_execution_id=integration.semantic_integration_execution_id,
            graph_name="agrotrace:demo",
            snapshot_label=f"snapshot-{run_code}",
            payload=payload,
            items=[{"item_key": "milk_production", "payload": {"liters": str(milk_liters)}}],
            published_at=now,
            canonical_snapshot_id=case_id(case_key, "canonical_snapshot", run_code),
            prov_entity_id=case_id(case_key, "prov_entity_snapshot", run_code),
            metadata={**meta, "demo_publication": "canonical_input"},
        ),
    )

    recorder.record_ontology_resource_link(
        uow,
        RecordOntologyResourceLinkCommand(
            pipeline_run_id=run.pipeline_run_id,
            canonical_snapshot_id=snapshot.canonical_snapshot_id,
            ontology_uri=f"https://ontology.demo.example/{run_code}",
            graph_name="agrotrace:demo",
            rdf_class="agro:CanonicalDataset",
            ontology_version=ONTOLOGY_VERSION,
            publication_stage=PublicationStage.CANONICAL_INPUT,
            published_at=now,
            ontology_resource_link_id=case_id(case_key, "ontology_link", run_code),
            metadata=meta,
        ),
    )

    # PROV attribute on snapshot entity
    uow.prov_attributes.add(
        ProvAttribute(
            prov_attribute_id=case_id(case_key, "attr", run_code),
            entity_id=snapshot.prov_entity_id,
            attr_key="milk_production_liters",
            attr_value={"value": str(milk_liters), "unit": "L"},
            recorded_at=now,
        )
    )

    params = recorder.record_calculation_parameter_set(
        uow,
        RecordCalculationParameterSetCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_method_version_id=catalog.calculation_method_version_id,
            values=[
                ParameterValueInput(
                    parameter_name="reporting_year",
                    parameter_value_text=reporting_period[:4],
                ),
            ],
            calculation_parameter_set_id=case_id(case_key, "parameter_set", run_code),
            prov_entity_id=case_id(case_key, "prov_entity_params", run_code),
        ),
    )

    calc_ex = recorder.record_calculation_execution(
        uow,
        RecordCalculationExecutionCommand(
            pipeline_run_id=run.pipeline_run_id,
            canonical_snapshot_id=snapshot.canonical_snapshot_id,
            calculation_method_version_id=catalog.calculation_method_version_id,
            calculation_parameter_set_id=params.calculation_parameter_set_id,
            started_at=now,
            finished_at=now,
            idempotency_key=idem_key(case_key, "calculation_execution", run_code),
            calculation_execution_id=case_id(case_key, "calculation_execution", run_code),
            prov_activity_id=case_id(case_key, "calculation_activity", run_code),
        ),
    )

    result_set = recorder.record_calculation_result_set(
        uow,
        RecordCalculationResultSetCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_execution_id=calc_ex.calculation_execution_id,
            items=[
                ResultItemInput(
                    result_type=CalculationResultType.PRODUCTIVITY,
                    result_name="milk_production",
                    result_value=milk_liters,
                    result_unit="L",
                ),
            ],
            generated_at=now,
            calculation_result_set_id=case_id(case_key, "result_set", run_code),
            prov_entity_id=case_id(case_key, "prov_entity_result", run_code),
            metadata=meta,
        ),
    )

    review = recorder.record_calculation_review(
        uow,
        RecordCalculationReviewCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_result_set_id=result_set.calculation_result_set_id,
            reviewer_agent_id=catalog.agent_reviewer_id,
            decision=CalculationReviewDecision.APPROVED,
            review_comment="Demo human approval.",
            calculation_review_id=case_id(case_key, "review", run_code),
            prov_activity_id=case_id(case_key, "review_activity", run_code),
        ),
    )

    publication_id: UUID | None = None
    if not skip_publication:
        pub = recorder.record_result_publication(
            uow,
            RecordResultPublicationCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_result_set_id=result_set.calculation_result_set_id,
                target_graph_name="agrotrace:published",
                ontology_name=ONTOLOGY_NAME,
                ontology_version=ONTOLOGY_VERSION,
                calculation_review_id=review.calculation_review_id,
                ontology_uri=f"https://ontology.demo.example/published/{run_code}",
                result_publication_execution_id=case_id(case_key, "publication", run_code),
                prov_activity_id=case_id(case_key, "publication_activity", run_code),
                metadata=meta,
            ),
        )
        publication_id = pub.result_publication_execution_id

        # Simulated blockchain anchor for hash already recorded on result_set
        hr = uow.hash_records.find_by_subject(
            HashSubjectKind.CALCULATION_RESULT_SET.value,
            result_set.calculation_result_set_id,
            HashAlgorithm.SHA256.value,
        )
        if hr is None:
            hr = recorder.record_hash(
                uow,
                RecordHashCommand(
                    pipeline_run_id=run.pipeline_run_id,
                    subject_kind=HashSubjectKind.CALCULATION_RESULT_SET,
                    subject_id=result_set.calculation_result_set_id,
                    hash_value=content_hash_label(f"{case_key}|result|{run_code}"),
                    prov_entity_id=result_set.prov_entity_id,
                    metadata={"demo": "published_result_hash"},
                ),
            )
        recorder.record_blockchain_anchor(
            uow,
            RecordBlockchainAnchorCommand(
                pipeline_run_id=run.pipeline_run_id,
                hash_record_id=hr.hash_record_id,
                blockchain_network="demo-chain",
                anchor_status=BlockchainAnchorStatus.CONFIRMED,
                transaction_hash=f"demo-tx-{run_code}",
                anchored_at=now,
                metadata={
                    "simulated": True,
                    "chain_name": "demo-chain",
                    "note": "Simulated anchor for demonstration only",
                },
            ),
        )

    return PipelineChainResult(
        pipeline_run_id=run.pipeline_run_id,
        run_code=run_code,
        source_artifact_id=artifact.source_artifact_id,
        source_prov_entity_id=artifact.prov_entity_id,
        normalized_batch_id=batch.normalized_batch_id,
        canonical_snapshot_id=snapshot.canonical_snapshot_id,
        canonical_prov_entity_id=snapshot.prov_entity_id,
        calculation_result_set_id=result_set.calculation_result_set_id,
        publication_execution_id=publication_id,
    )


def record_temporal_aggregation(
    uow: UnitOfWork,
    recorder: ProvenanceRecorder,
    *,
    case_key: str,
    run_code: str,
    farm_reference: str,
    reporting_period: str,
    catalog: SharedCatalog,
    aggregation_kind: str,
    source_snapshot_entity_ids: list[UUID],
    total_milk_liters: Decimal,
    source_run_codes: list[str],
    parent_pipeline_run_id: UUID | None = None,
) -> PipelineChainResult:
    """Create aggregation activity + aggregate canonical snapshot + full calc chain."""
    if uow.pipeline_runs.get_by_run_code(run_code) is not None:
        log(f"Skipping existing aggregation run {run_code!r}")
        existing = uow.pipeline_runs.get_by_run_code(run_code)
        assert existing is not None
        snaps = uow.canonical_snapshots.list_by_pipeline_run(existing.pipeline_run_id)
        rss = uow.calculation_result_sets.list_by_pipeline_run(existing.pipeline_run_id)
        return PipelineChainResult(
            pipeline_run_id=existing.pipeline_run_id,
            run_code=run_code,
            source_artifact_id=demo_id(case_key, "agg", "noop_art"),
            source_prov_entity_id=demo_id(case_key, "agg", "noop_se"),
            normalized_batch_id=demo_id(case_key, "agg", "noop_nb"),
            canonical_snapshot_id=snaps[0].canonical_snapshot_id if snaps else demo_id(case_key, "agg", "noop_cs"),
            canonical_prov_entity_id=snaps[0].prov_entity_id if snaps else demo_id(case_key, "agg", "noop_pe"),
            calculation_result_set_id=rss[0].calculation_result_set_id if rss else demo_id(case_key, "agg", "noop_rs"),
            has_aggregation=True,
            aggregation_kind=aggregation_kind,
            monthly_snapshot_entity_ids=source_snapshot_entity_ids,
        )

    now = utc_now()
    meta = {
        "demo_case": case_key,
        "aggregation_kind": aggregation_kind,
        "source_count": len(source_snapshot_entity_ids),
        "source_run_codes": source_run_codes,
        "total_milk_liters": str(total_milk_liters),
    }

    run = recorder.start_pipeline_run(
        uow,
        StartPipelineRunCommand(
            run_code=run_code,
            farm_reference=farm_reference,
            reporting_period_reference=reporting_period,
            triggered_by_agent_id=catalog.agent_trigger_id,
            parent_pipeline_run_id=parent_pipeline_run_id,
            idempotency_key=idem_key(case_key, "agg_run", run_code),
            pipeline_run_id=case_id(case_key, "agg_run", run_code),
            metadata=meta,
        ),
    )

    bundle_id = _ensure_pipeline_bundle(uow, run.pipeline_run_id)
    agg_activity_id = case_id(case_key, "agg_activity", run_code)
    uow.prov_activities.add(
        ProvActivity(
            activity_id=agg_activity_id,
            bundle_id=bundle_id,
            pipeline_run_id=run.pipeline_run_id,
            activity_type=ProvActivityType.OTHER,
            status="succeeded",
            name=aggregation_kind,
            business_key=aggregation_kind,
            started_at=now,
            ended_at=now,
            recorded_at=now,
            metadata={"demo_role": aggregation_kind},
        )
    )
    uow.flush()

    for src_entity_id in source_snapshot_entity_ids:
        uow.prov_relations.add_used(
            ProvUsed(
                used_id=new_uuid7(),
                activity_id=agg_activity_id,
                entity_id=src_entity_id,
                role="aggregation_input",
                used_at=now,
            )
        )

    agg_snapshot_id = case_id(case_key, "agg_snapshot", run_code)

    # Synthetic normalized batch for aggregation run (semantic/calc chain)
    ch = content_hash_label(f"{case_key}|agg_source|{run_code}")
    artifact = recorder.record_source_artifact(
        uow,
        RecordSourceArtifactCommand(
            pipeline_run_id=run.pipeline_run_id,
            source_system="demo_repo_aggregator",
            original_filename=f"{aggregation_kind}-{run_code}.json",
            storage_uri=f"demo://{run_code}/aggregate.json",
            content_hash=ch,
            received_at=now,
            idempotency_key=idem_key(case_key, "agg_source", run_code),
            source_artifact_id=case_id(case_key, "agg_source_artifact", run_code),
            prov_entity_id=case_id(case_key, "agg_source_entity", run_code),
            metadata=meta,
        ),
    )

    wrapper_ex = recorder.record_wrapper_execution(
        uow,
        RecordWrapperExecutionCommand(
            pipeline_run_id=run.pipeline_run_id,
            wrapper_definition_id=catalog.wrapper_definition_id,
            input_artifact_id=artifact.source_artifact_id,
            started_at=now,
            finished_at=now,
            idempotency_key=idem_key(case_key, "agg_wrapper", run_code),
            wrapper_execution_id=case_id(case_key, "agg_wrapper", run_code),
            prov_activity_id=case_id(case_key, "agg_wrapper_activity", run_code),
        ),
    )

    batch = recorder.record_normalized_batch(
        uow,
        RecordNormalizedBatchCommand(
            pipeline_run_id=run.pipeline_run_id,
            wrapper_execution_id=wrapper_ex.wrapper_execution_id,
            batch_code=f"NB-AGG-{run_code}",
            schema_version="1.0",
            record_count=len(source_snapshot_entity_ids),
            content_hash=content_hash_label(f"{case_key}|agg_batch|{run_code}"),
            generated_at=now,
            idempotency_key=idem_key(case_key, "agg_batch", run_code),
            normalized_batch_id=case_id(case_key, "agg_batch", run_code),
            prov_entity_id=case_id(case_key, "agg_batch_entity", run_code),
            metadata=meta,
        ),
    )

    integration = recorder.record_semantic_integration(
        uow,
        RecordSemanticIntegrationCommand(
            pipeline_run_id=run.pipeline_run_id,
            normalized_batch_id=batch.normalized_batch_id,
            ontology_name=ONTOLOGY_NAME,
            ontology_version=ONTOLOGY_VERSION,
            mapping_rule_version="1",
            started_at=now,
            finished_at=now,
            idempotency_key=idem_key(case_key, "agg_semantic", run_code),
            semantic_integration_execution_id=case_id(case_key, "agg_semantic", run_code),
            prov_activity_id=case_id(case_key, "agg_semantic_activity", run_code),
        ),
    )

    payload = {
        "aggregation_kind": aggregation_kind,
        "total_milk_liters": str(total_milk_liters),
        "input_count": len(source_snapshot_entity_ids),
    }
    snapshot = recorder.record_canonical_snapshot(
        uow,
        RecordCanonicalSnapshotCommand(
            pipeline_run_id=run.pipeline_run_id,
            semantic_integration_execution_id=integration.semantic_integration_execution_id,
            graph_name="agrotrace:demo",
            snapshot_label=f"{aggregation_kind}-{run_code}",
            payload=payload,
            items=[
                {
                    "item_key": "aggregate_total",
                    "payload": {"milk_liters": str(total_milk_liters)},
                }
            ],
            published_at=now,
            canonical_snapshot_id=agg_snapshot_id,
            prov_entity_id=case_id(case_key, "agg_snapshot_entity", run_code),
            metadata={**meta, "demo_role": aggregation_kind},
        ),
    )

    aggregate_entity_id = case_id(case_key, "aggregate_entity", run_code)
    uow.prov_entities.add(
        ProvEntity(
            entity_id=aggregate_entity_id,
            bundle_id=bundle_id,
            pipeline_run_id=run.pipeline_run_id,
            entity_type=ProvEntityType.OTHER,
            entity_kind=aggregation_kind.replace("_", "-"),
            name=aggregation_kind,
            created_at=now,
            content_hash=content_hash_label(f"{case_key}|{aggregation_kind}|{run_code}"),
            metadata={**meta, "canonical_snapshot_id": str(snapshot.canonical_snapshot_id)},
        )
    )
    uow.flush()
    uow.prov_relations.add_generated(
        ProvGenerated(
            generated_id=new_uuid7(),
            entity_id=aggregate_entity_id,
            activity_id=agg_activity_id,
            generated_at=now,
        )
    )
    for src_entity_id in source_snapshot_entity_ids:
        uow.prov_relations.add_derived_from(
            ProvDerivedFrom(
                derived_id=new_uuid7(),
                generated_entity_id=aggregate_entity_id,
                source_entity_id=src_entity_id,
                derivation_type=aggregation_kind,
            )
        )

    recorder.record_ontology_resource_link(
        uow,
        RecordOntologyResourceLinkCommand(
            pipeline_run_id=run.pipeline_run_id,
            canonical_snapshot_id=snapshot.canonical_snapshot_id,
            ontology_uri=f"https://ontology.demo.example/aggregate/{run_code}",
            graph_name="agrotrace:demo",
            rdf_class="agro:AggregateDataset",
            ontology_version=ONTOLOGY_VERSION,
            publication_stage=PublicationStage.CANONICAL_INPUT,
            published_at=now,
            ontology_resource_link_id=case_id(case_key, "agg_ontology", run_code),
            metadata=meta,
        ),
    )

    params = recorder.record_calculation_parameter_set(
        uow,
        RecordCalculationParameterSetCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_method_version_id=catalog.calculation_method_version_id,
            values=[
                ParameterValueInput(
                    parameter_name="aggregation_inputs",
                    parameter_value_numeric=Decimal(len(source_snapshot_entity_ids)),
                ),
            ],
            calculation_parameter_set_id=case_id(case_key, "agg_params", run_code),
            prov_entity_id=case_id(case_key, "agg_params_entity", run_code),
        ),
    )

    calc_ex = recorder.record_calculation_execution(
        uow,
        RecordCalculationExecutionCommand(
            pipeline_run_id=run.pipeline_run_id,
            canonical_snapshot_id=snapshot.canonical_snapshot_id,
            calculation_method_version_id=catalog.calculation_method_version_id,
            calculation_parameter_set_id=params.calculation_parameter_set_id,
            started_at=now,
            finished_at=now,
            idempotency_key=idem_key(case_key, "agg_calc", run_code),
            calculation_execution_id=case_id(case_key, "agg_calc", run_code),
            prov_activity_id=case_id(case_key, "agg_calc_activity", run_code),
        ),
    )

    result_set = recorder.record_calculation_result_set(
        uow,
        RecordCalculationResultSetCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_execution_id=calc_ex.calculation_execution_id,
            items=[
                ResultItemInput(
                    result_type=CalculationResultType.PRODUCTIVITY,
                    result_name="aggregated_milk_production",
                    result_value=total_milk_liters,
                    result_unit="L",
                ),
            ],
            generated_at=now,
            calculation_result_set_id=case_id(case_key, "agg_result", run_code),
            prov_entity_id=case_id(case_key, "agg_result_entity", run_code),
            metadata=meta,
        ),
    )

    review = recorder.record_calculation_review(
        uow,
        RecordCalculationReviewCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_result_set_id=result_set.calculation_result_set_id,
            reviewer_agent_id=catalog.agent_reviewer_id,
            decision=CalculationReviewDecision.APPROVED,
            review_comment=f"Approved {aggregation_kind}.",
            calculation_review_id=case_id(case_key, "agg_review", run_code),
            prov_activity_id=case_id(case_key, "agg_review_activity", run_code),
        ),
    )

    pub = recorder.record_result_publication(
        uow,
        RecordResultPublicationCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_result_set_id=result_set.calculation_result_set_id,
            target_graph_name="agrotrace:published",
            ontology_name=ONTOLOGY_NAME,
            ontology_version=ONTOLOGY_VERSION,
            calculation_review_id=review.calculation_review_id,
            ontology_uri=f"https://ontology.demo.example/published/aggregate/{run_code}",
            result_publication_execution_id=case_id(case_key, "agg_publication", run_code),
            prov_activity_id=case_id(case_key, "agg_publication_activity", run_code),
            metadata=meta,
        ),
    )

    hr = uow.hash_records.find_by_subject(
        HashSubjectKind.CANONICAL_SNAPSHOT.value,
        snapshot.canonical_snapshot_id,
        HashAlgorithm.SHA256.value,
    )
    if hr is None:
        hr = recorder.record_hash(
            uow,
            RecordHashCommand(
                pipeline_run_id=run.pipeline_run_id,
                subject_kind=HashSubjectKind.CANONICAL_SNAPSHOT,
                subject_id=snapshot.canonical_snapshot_id,
                hash_value=snapshot.snapshot_hash,
                prov_entity_id=snapshot.prov_entity_id,
                metadata={"demo": aggregation_kind},
            ),
        )
    recorder.record_blockchain_anchor(
        uow,
        RecordBlockchainAnchorCommand(
            pipeline_run_id=run.pipeline_run_id,
            hash_record_id=hr.hash_record_id,
            blockchain_network="demo-chain",
            anchor_status=BlockchainAnchorStatus.CONFIRMED,
            transaction_hash=f"demo-tx-agg-{run_code}",
            anchored_at=now,
            metadata={"simulated": True, "aggregation_kind": aggregation_kind},
        ),
    )

    uow.audit_events.add(
        AuditEvent(
            audit_event_id=case_id(case_key, "audit", run_code),
            event_type=f"demo.{aggregation_kind}.completed",
            actor_agent_id=catalog.agent_system_id,
            subject_kind="canonical_snapshot",
            subject_id=snapshot.canonical_snapshot_id,
            payload={"source_count": len(source_snapshot_entity_ids), **meta},
            recorded_at=now,
        )
    )

    _ = pub
    return PipelineChainResult(
        pipeline_run_id=run.pipeline_run_id,
        run_code=run_code,
        source_artifact_id=artifact.source_artifact_id,
        source_prov_entity_id=artifact.prov_entity_id,
        normalized_batch_id=batch.normalized_batch_id,
        canonical_snapshot_id=snapshot.canonical_snapshot_id,
        canonical_prov_entity_id=snapshot.prov_entity_id,
        calculation_result_set_id=result_set.calculation_result_set_id,
        publication_execution_id=pub.result_publication_execution_id,
        has_aggregation=True,
        aggregation_kind=aggregation_kind,
        monthly_snapshot_entity_ids=source_snapshot_entity_ids,
    )


def record_demo_audit_event(
    uow: UnitOfWork,
    *,
    event_type: str,
    subject_kind: str,
    subject_id: UUID,
    actor_agent_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    uow.audit_events.add(
        AuditEvent(
            audit_event_id=new_uuid7(),
            event_type=event_type,
            actor_agent_id=actor_agent_id,
            subject_kind=subject_kind,
            subject_id=subject_id,
            payload=payload or {},
            recorded_at=utcnow(),
        )
    )


def open_uow():
    from demo_config import create_session_stack

    _, sf, _ = create_session_stack()
    return SqlAlchemyUnitOfWork(sf), ProvenanceRecorder()
