"""Full end-to-end recorder flow against PostgreSQL via testcontainers."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from provenance_service.application.services.provenance_recorder import (
    ParameterValueInput,
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
    RecordResultPublicationCommand,
    RecordSemanticIntegrationCommand,
    RecordSourceArtifactCommand,
    RecordWrapperDefinitionCommand,
    RecordWrapperExecutionCommand,
    ResultItemInput,
    StartPipelineRunCommand,
)
from provenance_service.domain.prov_core.entities import ProvAgent
from provenance_service.domain.shared.enums import (
    BlockchainAnchorStatus,
    CalculationResultSetStatus,
    CalculationResultType,
    CalculationReviewDecision,
    HashAlgorithm,
    HashSubjectKind,
    OutboxStatus,
    ProvAgentType,
)
from provenance_service.domain.shared.ids import new_uuid7
from provenance_service.domain.shared.time import utcnow


def test_full_flow_records_pipeline_run_to_anchor(uow_factory, recorder) -> None:
    with uow_factory() as uow:
        run = recorder.start_pipeline_run(
            uow,
            StartPipelineRunCommand(
                run_code="run-int-001",
                farm_reference="farm-int",
                reporting_period_reference="2026-Q1",
            ),
        )
        artifact = recorder.record_source_artifact(
            uow,
            RecordSourceArtifactCommand(
                pipeline_run_id=run.pipeline_run_id,
                source_system="ERP",
                original_filename="payload.xml",
                storage_uri="s3://raw/payload.xml",
                content_hash="a" * 64,
            ),
        )
        definition = recorder.record_wrapper_definition(
            uow,
            RecordWrapperDefinitionCommand(
                wrapper_name="erp-xml",
                wrapper_version="1.0.0",
                source_layout_name="erp",
            ),
        )
        execution = recorder.record_wrapper_execution(
            uow,
            RecordWrapperExecutionCommand(
                pipeline_run_id=run.pipeline_run_id,
                wrapper_definition_id=definition.wrapper_definition_id,
                input_artifact_id=artifact.source_artifact_id,
                started_at=datetime.now(timezone.utc),
            ),
        )
        batch = recorder.record_normalized_batch(
            uow,
            RecordNormalizedBatchCommand(
                pipeline_run_id=run.pipeline_run_id,
                wrapper_execution_id=execution.wrapper_execution_id,
                batch_code="batch-int-1",
                schema_version="1.0",
                record_count=5,
                content_hash="b" * 64,
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
                started_at=datetime.now(timezone.utc),
            ),
        )
        snapshot = recorder.record_canonical_snapshot(
            uow,
            RecordCanonicalSnapshotCommand(
                pipeline_run_id=run.pipeline_run_id,
                semantic_integration_execution_id=(
                    integration.semantic_integration_execution_id
                ),
                graph_name="agrotrace:graph",
                snapshot_label="snap-int-1",
                payload={"farms": ["farm-int"]},
            ),
        )
        method = recorder.record_calculation_method(
            uow,
            RecordCalculationMethodCommand(
                method_code="ipcc-2019",
                method_name="IPCC 2019 Refinement",
            ),
        )
        version = recorder.record_calculation_method_version(
            uow,
            RecordCalculationMethodVersionCommand(
                calculation_method_id=method.calculation_method_id,
                version_label="1.0",
            ),
        )
        params = recorder.record_calculation_parameter_set(
            uow,
            RecordCalculationParameterSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_method_version_id=version.calculation_method_version_id,
                values=[
                    ParameterValueInput(
                        parameter_name="ef_methane",
                        parameter_value_numeric=Decimal("28.0"),
                        parameter_unit="kg",
                    )
                ],
            ),
        )
        calc_exec = recorder.record_calculation_execution(
            uow,
            RecordCalculationExecutionCommand(
                pipeline_run_id=run.pipeline_run_id,
                canonical_snapshot_id=snapshot.canonical_snapshot_id,
                calculation_method_version_id=version.calculation_method_version_id,
                calculation_parameter_set_id=params.calculation_parameter_set_id,
                started_at=datetime.now(timezone.utc),
            ),
        )
        result_set = recorder.record_calculation_result_set(
            uow,
            RecordCalculationResultSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_execution_id=calc_exec.calculation_execution_id,
                items=[
                    ResultItemInput(
                        result_type=CalculationResultType.EMISSION_TOTAL,
                        result_name="co2e_total",
                        result_value=Decimal("999.99"),
                        result_unit="kgCO2e",
                    )
                ],
            ),
        )

        reviewer_id = new_uuid7()
        uow.prov_agents.add(
            ProvAgent(
                agent_id=reviewer_id,
                agent_type=ProvAgentType.HUMAN,
                name="reviewer-int",
                external_reference="user:reviewer-int",
                created_at=utcnow(),
            )
        )
        review = recorder.record_calculation_review(
            uow,
            RecordCalculationReviewCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_result_set_id=result_set.calculation_result_set_id,
                reviewer_agent_id=reviewer_id,
                decision=CalculationReviewDecision.APPROVED,
            ),
        )
        publication = recorder.record_result_publication(
            uow,
            RecordResultPublicationCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_result_set_id=result_set.calculation_result_set_id,
                target_graph_name="agrotrace:final",
                ontology_name="agrotrace",
                ontology_version="2026.04",
                calculation_review_id=review.calculation_review_id,
                ontology_uri="urn:agrotrace:result:int-1",
                rdf_class="agro:CarbonResult",
            ),
        )
        hash_record = recorder.record_hash(
            uow,
            RecordHashCommand(
                pipeline_run_id=run.pipeline_run_id,
                subject_kind=HashSubjectKind.BUNDLE,
                subject_id=publication.result_publication_execution_id,
                hash_value="d" * 64,
                hash_algorithm=HashAlgorithm.SHA256,
            ),
        )
        anchor = recorder.record_blockchain_anchor(
            uow,
            RecordBlockchainAnchorCommand(
                pipeline_run_id=run.pipeline_run_id,
                hash_record_id=hash_record.hash_record_id,
                blockchain_network="stub",
                anchor_status=BlockchainAnchorStatus.SUBMITTED,
                transaction_hash="0xint",
            ),
        )
        uow.commit()

    with uow_factory() as uow2:
        assert uow2.pipeline_runs.get(run.pipeline_run_id) is not None
        assert uow2.source_artifacts.get(artifact.source_artifact_id) is not None
        assert uow2.normalized_batches.get(batch.normalized_batch_id) is not None
        assert uow2.canonical_snapshots.get(snapshot.canonical_snapshot_id) is not None
        assert (
            uow2.calculation_executions.get(calc_exec.calculation_execution_id)
            is not None
        )
        rs = uow2.calculation_result_sets.get(result_set.calculation_result_set_id)
        assert rs is not None
        assert rs.result_set_status is CalculationResultSetStatus.APPROVED
        assert uow2.calculation_reviews.get(review.calculation_review_id) is not None
        assert (
            uow2.result_publication_executions.get(
                publication.result_publication_execution_id
            )
            is not None
        )
        assert uow2.hash_records.get(hash_record.hash_record_id) is not None
        assert uow2.blockchain_anchors.get(anchor.blockchain_anchor_id) is not None
        pending = uow2.outbox.list_pending(1000)
        assert any(e.event_type == "pipeline_run.started" for e in pending)
        assert any(e.event_type.startswith("blockchain_anchor.") for e in pending)
        assert all(e.status is OutboxStatus.PENDING for e in pending)
