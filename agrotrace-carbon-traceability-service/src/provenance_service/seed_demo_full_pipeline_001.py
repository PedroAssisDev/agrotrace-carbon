"""Idempotent seed for scenario ``demo_full_pipeline_001``.

Run: ``python -m provenance_service.seed_demo_full_pipeline_001`` (with
``PROV_DATABASE_URL`` pointing at your database and tables created). For the
default SQLite checkout, run ``provenance-init-local-db`` first. Idempotent on
``run_code``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from provenance_service.application.services.provenance_recorder import (
    ParameterValueInput,
    ProvenanceRecorder,
    RecordCalculationExecutionCommand,
    RecordCalculationMethodCommand,
    RecordCalculationMethodVersionCommand,
    RecordCalculationParameterSetCommand,
    RecordCalculationResultSetCommand,
    RecordCalculationReviewCommand,
    RecordCanonicalSnapshotCommand,
    RecordHashCommand,
    RecordNormalizedBatchCommand,
    RecordResultPublicationCommand,
    RecordSemanticIntegrationCommand,
    RecordSourceArtifactCommand,
    RecordSourceArtifactRevisionCommand,
    RecordWrapperDefinitionCommand,
    RecordWrapperExecutionCommand,
    ResultItemInput,
    StartPipelineRunCommand,
)
from provenance_service.domain.prov_core.entities import ProvAgent
from provenance_service.domain.semantic.entities import OntologyResourceLink
from provenance_service.domain.shared.enums import (
    CalculationResultType,
    CalculationReviewDecision,
    HashAlgorithm,
    HashSubjectKind,
    ProvAgentType,
    ProvBundleType,
    PublicationStage,
)
from provenance_service.domain.shared.hashing import compute_hash_hex
from provenance_service.domain.shared.time import utcnow
from provenance_service.infrastructure.config import get_settings
from provenance_service.infrastructure.db.session import (
    create_engine_from_settings,
    create_sessionmaker,
)
from provenance_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

DEMO_NS = uuid.UUID("11111111-1111-1111-1111-111111111111")
RUN_CODE = "RUN-DEMO-2026-03-001"


def _did(part: str) -> uuid.UUID:
    return uuid.uuid5(DEMO_NS, f"demo_full_pipeline_001|{part}")


def _hex_label(label: str) -> str:
    return compute_hash_hex({"demo_full_pipeline_001": label})


def main() -> None:
    get_settings.cache_clear()  # type: ignore[attr-defined]
    settings = get_settings()
    engine = create_engine_from_settings(settings)
    sf = create_sessionmaker(engine)
    recorder = ProvenanceRecorder()
    now = datetime.now(timezone.utc)

    with SqlAlchemyUnitOfWork(sf) as uow:
        if uow.pipeline_runs.get_by_run_code(RUN_CODE) is not None:
            print(f"Seed skipped: pipeline run {RUN_CODE!r} already exists.")
            return

        pedro = _did("agent_pedro")
        ana = _did("agent_ana")
        uow.prov_agents.add(
            ProvAgent(
                agent_id=pedro,
                agent_type=ProvAgentType.HUMAN,
                name="Pedro (trigger)",
                external_reference="user:pedro-demo",
                created_at=utcnow(),
                metadata={"demo_role": "pipeline_trigger"},
            )
        )
        uow.prov_agents.add(
            ProvAgent(
                agent_id=ana,
                agent_type=ProvAgentType.HUMAN,
                name="Ana (reviewer)",
                external_reference="user:ana-demo",
                created_at=utcnow(),
                metadata={"demo_role": "reviewer"},
            )
        )
        uow.flush()

        pipeline_run_id = _did("pipeline_run")
        run = recorder.start_pipeline_run(
            uow,
            StartPipelineRunCommand(
                run_code=RUN_CODE,
                farm_reference="DEMO-FARM-001",
                reporting_period_reference="2026-03",
                tenant_id=DEMO_NS,
                triggered_by_agent_id=pedro,
                notes="demo_full_pipeline_001",
                pipeline_run_id=pipeline_run_id,
                metadata={"scenario": "demo_full_pipeline_001"},
            ),
        )

        content_hash = _hex_label("source_csv")
        artifact = recorder.record_source_artifact(
            uow,
            RecordSourceArtifactCommand(
                pipeline_run_id=run.pipeline_run_id,
                source_system="demo_erp",
                original_filename="inventario_marco_2026.csv",
                storage_uri="s3://demo-bucket/raw/inventario_marco_2026.csv",
                content_hash=content_hash,
                received_at=now,
                source_artifact_id=_did("source_artifact"),
                prov_entity_id=_did("prov_entity_source_artifact"),
                metadata={"demo": "initial_upload"},
            ),
        )

        revision = recorder.record_source_artifact_revision(
            uow,
            RecordSourceArtifactRevisionCommand(
                source_artifact_id=artifact.source_artifact_id,
                revision_number=1,
                storage_uri="s3://demo-bucket/raw/inventario_marco_2026_v1.csv",
                content_hash=_hex_label("source_csv_rev1"),
                received_at=now,
                source_artifact_revision_id=_did("source_artifact_revision"),
                prov_entity_id=_did("prov_entity_source_artifact_revision"),
                metadata={"demo": "corrected_revision"},
            ),
        )

        wrapper_def = recorder.record_wrapper_definition(
            uow,
            RecordWrapperDefinitionCommand(
                wrapper_name="demo-csv-normalizer",
                wrapper_version="1.0.0",
                source_layout_name="demo_csv",
                wrapper_definition_id=_did("wrapper_definition"),
                metadata={"demo": True},
            ),
        )

        wrapper_ex = recorder.record_wrapper_execution(
            uow,
            RecordWrapperExecutionCommand(
                pipeline_run_id=run.pipeline_run_id,
                wrapper_definition_id=wrapper_def.wrapper_definition_id,
                input_artifact_id=artifact.source_artifact_id,
                started_at=now,
                input_source_artifact_revision_id=revision.source_artifact_revision_id,
                wrapper_execution_id=_did("wrapper_execution"),
                prov_activity_id=_did("wrapper_activity"),
            ),
        )

        batch = recorder.record_normalized_batch(
            uow,
            RecordNormalizedBatchCommand(
                pipeline_run_id=run.pipeline_run_id,
                wrapper_execution_id=wrapper_ex.wrapper_execution_id,
                batch_code="NB-DEMO-001",
                schema_version="1.0",
                record_count=120,
                content_hash=_hex_label("normalized_batch"),
                generated_at=now,
                normalized_batch_id=_did("normalized_batch"),
                prov_entity_id=_did("prov_entity_normalized_batch"),
            ),
        )

        integration = recorder.record_semantic_integration(
            uow,
            RecordSemanticIntegrationCommand(
                pipeline_run_id=run.pipeline_run_id,
                normalized_batch_id=batch.normalized_batch_id,
                ontology_name="agrotrace",
                ontology_version="2026.04",
                mapping_rule_version="1",
                started_at=now,
                semantic_integration_execution_id=_did("semantic_integration"),
                prov_activity_id=_did("semantic_activity"),
            ),
        )

        snapshot = recorder.record_canonical_snapshot(
            uow,
            RecordCanonicalSnapshotCommand(
                pipeline_run_id=run.pipeline_run_id,
                semantic_integration_execution_id=integration.semantic_integration_execution_id,
                graph_name="agrotrace:demo",
                snapshot_label="canonical-demo-001",
                payload={"farm_id": "DEMO-FARM-001", "period": "2026-03"},
                items=[{"item_key": "row-1", "payload": {"co2e": 12.3}}],
                published_at=now,
                canonical_snapshot_id=_did("canonical_snapshot"),
                prov_entity_id=_did("prov_entity_canonical_snapshot"),
            ),
        )

        uow.ontology_resource_links.add(
            OntologyResourceLink(
                ontology_resource_link_id=_did("ontology_link_snapshot"),
                pipeline_run_id=run.pipeline_run_id,
                prov_entity_id=None,
                canonical_snapshot_id=snapshot.canonical_snapshot_id,
                ontology_uri="https://ontology.demo.example/agrotrace/canonical/snapshot-001",
                rdf_class="agro:CanonicalDataset",
                graph_name="agrotrace:demo",
                ontology_version="2026.04",
                publication_stage=PublicationStage.CANONICAL_INPUT,
                published_at=now,
                metadata={"demo": "snapshot_ontology_link"},
            )
        )

        method = recorder.record_calculation_method(
            uow,
            RecordCalculationMethodCommand(
                method_code="demo-ghg-2026",
                method_name="Demo GHG inventory method",
                calculation_method_id=_did("calculation_method"),
            ),
        )
        version = recorder.record_calculation_method_version(
            uow,
            RecordCalculationMethodVersionCommand(
                calculation_method_id=method.calculation_method_id,
                version_label="1.0.0",
                calculation_method_version_id=_did("calculation_method_version"),
            ),
        )
        params = recorder.record_calculation_parameter_set(
            uow,
            RecordCalculationParameterSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_method_version_id=version.calculation_method_version_id,
                values=[
                    ParameterValueInput(
                        parameter_name="gwp100_ch4",
                        parameter_value_numeric=Decimal("28"),
                        parameter_unit="kgCO2e/kg",
                    )
                ],
                calculation_parameter_set_id=_did("calculation_parameter_set"),
                prov_entity_id=_did("prov_entity_parameter_set"),
            ),
        )
        calc_ex = recorder.record_calculation_execution(
            uow,
            RecordCalculationExecutionCommand(
                pipeline_run_id=run.pipeline_run_id,
                canonical_snapshot_id=snapshot.canonical_snapshot_id,
                calculation_method_version_id=version.calculation_method_version_id,
                calculation_parameter_set_id=params.calculation_parameter_set_id,
                started_at=now,
                calculation_execution_id=_did("calculation_execution"),
                prov_activity_id=_did("calculation_activity"),
            ),
        )
        result_set = recorder.record_calculation_result_set(
            uow,
            RecordCalculationResultSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_execution_id=calc_ex.calculation_execution_id,
                items=[
                    ResultItemInput(
                        result_type=CalculationResultType.GHG_EMISSION,
                        result_name="total_ghg",
                        result_value=Decimal("142.5"),
                        result_unit="tCO2e",
                    ),
                    ResultItemInput(
                        result_type=CalculationResultType.CARBON_FOOTPRINT,
                        result_name="footprint_intensity",
                        result_value=Decimal("1.02"),
                        result_unit="tCO2e/ha",
                    ),
                ],
                generated_at=now,
                metadata={
                    "demo_label": "sha256_result_set_demo_001",
                    "note": "summary_hash is deterministic from items+execution_id",
                },
                calculation_result_set_id=_did("calculation_result_set"),
                prov_entity_id=_did("prov_entity_result_set"),
            ),
        )

        review = recorder.record_calculation_review(
            uow,
            RecordCalculationReviewCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_result_set_id=result_set.calculation_result_set_id,
                reviewer_agent_id=ana,
                decision=CalculationReviewDecision.APPROVED,
                review_comment="Approved for demo publication.",
                calculation_review_id=_did("calculation_review"),
                prov_activity_id=_did("calculation_review_activity"),
            ),
        )

        publication = recorder.record_result_publication(
            uow,
            RecordResultPublicationCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_result_set_id=result_set.calculation_result_set_id,
                target_graph_name="agrotrace:published",
                ontology_name="agrotrace",
                ontology_version="2026.04",
                calculation_review_id=review.calculation_review_id,
                ontology_uri="https://ontology.demo.example/agrotrace/result/demo-001",
                rdf_class="agro:PublishedCarbonResult",
                result_publication_execution_id=_did("result_publication"),
                prov_activity_id=_did("result_publication_activity"),
            ),
        )

        calc_bundle = next(
            b
            for b in uow.prov_bundles.list_by_pipeline_run(run.pipeline_run_id)
            if b.bundle_type is ProvBundleType.CALCULATION
        )
        recorder.record_hash(
            uow,
            RecordHashCommand(
                pipeline_run_id=run.pipeline_run_id,
                subject_kind=HashSubjectKind.BUNDLE,
                subject_id=calc_bundle.bundle_id,
                hash_value=_hex_label("anchor_bundle_calculation"),
                hash_algorithm=HashAlgorithm.SHA256,
                bundle_id=calc_bundle.bundle_id,
                metadata={"demo": "bundle_anchor"},
            ),
        )

        _ = publication
        uow.commit()

    print(f"Seed completed: pipeline_run_id={pipeline_run_id}")


if __name__ == "__main__":
    main()
