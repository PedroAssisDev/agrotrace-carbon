"""Integration tests for blockchain observability preparation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError

from provenance_service.application.services.provenance_recorder import (
    ParameterValueInput,
    RecordCalculationExecutionCommand,
    RecordCalculationMethodCommand,
    RecordCalculationMethodVersionCommand,
    RecordCalculationParameterSetCommand,
    RecordCalculationResultSetCommand,
    RecordCalculationReviewCommand,
    RecordCanonicalSnapshotCommand,
    RecordNormalizedBatchCommand,
    RecordReportingPeriodCommand,
    RecordResultAggregationLinkCommand,
    RecordResultPublicationCommand,
    RecordSemanticIntegrationCommand,
    RecordSourceArtifactCommand,
    RecordWrapperDefinitionCommand,
    RecordWrapperExecutionCommand,
    ResultItemInput,
    StartPipelineRunCommand,
)
from provenance_service.domain.shared.enums import (
    AggregationType,
    CalculationExecutionStatus,
    CalculationResultSetStatus,
    CalculationResultType,
    CalculationReviewDecision,
    ConsolidationType,
    OutboxStatus,
    ParameterSetStatus,
    PeriodGranularity,
    ReportingPeriodStatus,
    ResultPublicationStatus,
    ResultScope,
    RunType,
    WrapperExecutionStatus,
)
from provenance_service.domain.shared.ids import new_uuid7
from provenance_service.infrastructure.db.models.calculation import (
    CalculationParameterValueModel,
)


def _utc(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=timezone.utc)


def _seed_agent(uow_factory, recorder):
    from provenance_service.domain.prov_core.entities import ProvAgent
    from provenance_service.domain.shared.enums import ProvAgentType

    agent_id = new_uuid7()
    with uow_factory() as uow:
        uow.prov_agents.add(
            ProvAgent(
                agent_id=agent_id,
                agent_type=ProvAgentType.HUMAN,
                name="reviewer",
                external_reference="reviewer@test",
                created_at=datetime.now(timezone.utc),
            )
        )
        uow.commit()
    return agent_id


def _seed_calculation_flow(uow_factory, recorder, *, period_id=None):
    agent_id = _seed_agent(uow_factory, recorder)
    method_id = new_uuid7()
    version_id = new_uuid7()
    with uow_factory() as uow:
        run = recorder.start_pipeline_run(
            uow,
            StartPipelineRunCommand(
                run_code=f"obs-{new_uuid7().hex[:8]}",
                farm_reference="farm-obs",
                reporting_period_reference="2026-01",
                run_type=RunType.MONTHLY_CALCULATION,
                reporting_period_id=period_id,
            ),
        )
        artifact = recorder.record_source_artifact(
            uow,
            RecordSourceArtifactCommand(
                pipeline_run_id=run.pipeline_run_id,
                source_system="ERP",
                original_filename="data.csv",
                storage_uri="s3://data.csv",
                content_hash="a" * 64,
                received_at=_utc(2026, 1, 1),
            ),
        )
        wrapper = recorder.record_wrapper_definition(
            uow,
            RecordWrapperDefinitionCommand(
                wrapper_name="csv-wrapper",
                wrapper_version="1.0",
                source_layout_name="csv",
            ),
        )
        execution = recorder.record_wrapper_execution(
            uow,
            RecordWrapperExecutionCommand(
                pipeline_run_id=run.pipeline_run_id,
                wrapper_definition_id=wrapper.wrapper_definition_id,
                input_artifact_id=artifact.source_artifact_id,
                started_at=_utc(2026, 1, 1),
                execution_status=WrapperExecutionStatus.SUCCEEDED,
            ),
        )
        recorder.record_calculation_method(
            uow, RecordCalculationMethodCommand(method_code="m1", method_name="Method 1")
        )
        uow.commit()

    with uow_factory() as uow:
        method = uow.calculation_methods.get_by_code("m1")
        assert method is not None
        method_id = method.calculation_method_id
        version = recorder.record_calculation_method_version(
            uow,
            RecordCalculationMethodVersionCommand(
                calculation_method_id=method_id,
                version_label="v1",
            ),
        )
        version_id = version.calculation_method_version_id
        uow.commit()

    return run, agent_id, method_id, version_id


def _outbox_events(uow_factory):
    with uow_factory() as uow:
        pending, _ = uow.outbox.list_filtered(limit=500, offset=0)
        return pending


# ---- Events ----


def test_calculation_approved_event_created(uow_factory, recorder) -> None:
    period_id = _create_monthly_period(uow_factory, recorder).reporting_period_id
    run, agent_id, method_id, version_id = _seed_calculation_flow(
        uow_factory, recorder, period_id=period_id
    )
    rs_id = _create_preliminary_result(
        uow_factory, recorder, run, agent_id, method_id, version_id, period_id
    )
    with uow_factory() as uow:
        recorder.record_calculation_review(
            uow,
            RecordCalculationReviewCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_result_set_id=rs_id,
                reviewer_agent_id=agent_id,
                decision=CalculationReviewDecision.APPROVED,
                reporting_period_id=period_id,
            ),
        )
        uow.commit()
    events = _outbox_events(uow_factory)
    approved = [e for e in events if e.event_type == "CALCULATION_APPROVED"]
    assert len(approved) >= 1
    assert approved[0].status is OutboxStatus.PENDING
    assert approved[0].payload["calculation_result_set_id"] == str(rs_id)


def test_approved_result_published_event(uow_factory, recorder) -> None:
    period_id = _create_monthly_period(uow_factory, recorder).reporting_period_id
    run, agent_id, method_id, version_id = _seed_calculation_flow(
        uow_factory, recorder, period_id=period_id
    )
    rs_id = _create_preliminary_result(
        uow_factory, recorder, run, agent_id, method_id, version_id, period_id
    )
    with uow_factory() as uow:
        recorder.record_calculation_review(
            uow,
            RecordCalculationReviewCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_result_set_id=rs_id,
                reviewer_agent_id=agent_id,
                decision=CalculationReviewDecision.APPROVED,
            ),
        )
        recorder.record_result_publication(
            uow,
            RecordResultPublicationCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_result_set_id=rs_id,
                target_graph_name="graph:final",
                ontology_name="agrotrace",
                ontology_version="2026",
                publication_status=ResultPublicationStatus.PUBLISHED,
                ontology_uri="http://ontology/result/1",
                publication_payload_hash="b" * 64,
            ),
        )
        uow.commit()
    events = _outbox_events(uow_factory)
    assert any(e.event_type == "APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY" for e in events)


def test_monthly_result_consolidated_event(uow_factory, recorder) -> None:
    period_id = _create_monthly_period(uow_factory, recorder).reporting_period_id
    run, agent_id, method_id, version_id = _seed_calculation_flow(
        uow_factory, recorder, period_id=period_id
    )
    with uow_factory() as uow:
        rs = recorder.record_calculation_result_set(
            uow,
            RecordCalculationResultSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_execution_id=_create_execution(
                    uow, recorder, run, method_id, version_id, period_id
                ).calculation_execution_id,
                items=[
                    ResultItemInput(
                        result_type=CalculationResultType.GHG_EMISSION,
                        result_name="total",
                        result_value=Decimal("100"),
                        result_unit="kg",
                    )
                ],
                reporting_period_id=period_id,
                result_scope=ResultScope.MONTHLY,
                consolidation_type=ConsolidationType.DAILY_TO_MONTHLY,
            ),
        )
        uow.commit()
    events = _outbox_events(uow_factory)
    assert any(e.event_type == "MONTHLY_RESULT_CONSOLIDATED" for e in events)


def test_annual_result_consolidated_event(uow_factory, recorder) -> None:
    period_id = _create_annual_period(uow_factory, recorder).reporting_period_id
    run, agent_id, method_id, version_id = _seed_calculation_flow(
        uow_factory, recorder, period_id=period_id
    )
    with uow_factory() as uow:
        recorder.record_calculation_result_set(
            uow,
            RecordCalculationResultSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_execution_id=_create_execution(
                    uow, recorder, run, method_id, version_id, period_id
                ).calculation_execution_id,
                items=[
                    ResultItemInput(
                        result_type=CalculationResultType.GHG_EMISSION,
                        result_name="annual",
                        result_value=Decimal("1200"),
                        result_unit="kg",
                    )
                ],
                reporting_period_id=period_id,
                result_scope=ResultScope.ANNUAL,
                consolidation_type=ConsolidationType.MONTHLY_TO_ANNUAL,
            ),
        )
        uow.commit()
    events = _outbox_events(uow_factory)
    assert any(e.event_type == "ANNUAL_RESULT_CONSOLIDATED" for e in events)


def test_outbox_event_starts_pending_with_valid_payload(uow_factory, recorder) -> None:
    period_id = _create_monthly_period(uow_factory, recorder).reporting_period_id
    run, agent_id, method_id, version_id = _seed_calculation_flow(
        uow_factory, recorder, period_id=period_id
    )
    rs_id = _create_preliminary_result(
        uow_factory, recorder, run, agent_id, method_id, version_id, period_id
    )
    with uow_factory() as uow:
        recorder.record_calculation_review(
            uow,
            RecordCalculationReviewCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_result_set_id=rs_id,
                reviewer_agent_id=agent_id,
                decision=CalculationReviewDecision.APPROVED,
            ),
        )
        uow.commit()
    events = _outbox_events(uow_factory)
    evt = next(e for e in events if e.event_type == "CALCULATION_APPROVED")
    assert evt.status is OutboxStatus.PENDING
    assert isinstance(evt.payload, dict)
    assert evt.payload["event_type"] == "CALCULATION_APPROVED"


# ---- Reporting period ----


def test_create_daily_reporting_period(uow_factory, recorder) -> None:
    with uow_factory() as uow:
        period = recorder.record_reporting_period(
            uow,
            RecordReportingPeriodCommand(
                period_start=_utc(2026, 1, 15),
                period_end=_utc(2026, 1, 16),
                period_granularity=PeriodGranularity.DAILY,
                year=2026,
                month=1,
                day=15,
                period_label="2026-01-15",
            ),
        )
        uow.commit()
    assert period.period_granularity is PeriodGranularity.DAILY
    assert period.day == 15


def test_create_monthly_reporting_period(uow_factory, recorder) -> None:
    period = _create_monthly_period(uow_factory, recorder)
    assert period.period_granularity is PeriodGranularity.MONTHLY
    assert period.month == 1


def test_create_annual_reporting_period(uow_factory, recorder) -> None:
    period = _create_annual_period(uow_factory, recorder)
    assert period.period_granularity is PeriodGranularity.ANNUAL
    assert period.year == 2026


def test_invalid_period_granularity_rejected() -> None:
    with pytest.raises(ValueError):
        PeriodGranularity("invalid_granularity")


def test_daily_period_requires_day(uow_factory, recorder) -> None:
    with uow_factory() as uow:
        with pytest.raises(Exception):
            recorder.record_reporting_period(
                uow,
                RecordReportingPeriodCommand(
                    period_start=_utc(2026, 1, 1),
                    period_end=_utc(2026, 1, 2),
                    period_granularity=PeriodGranularity.DAILY,
                    year=2026,
                    month=1,
                    period_label="2026-01-01-missing-day",
                ),
            )


# ---- Result set ----


def test_monthly_result_set_with_reporting_period(uow_factory, recorder) -> None:
    period_id = _create_monthly_period(uow_factory, recorder).reporting_period_id
    run, agent_id, method_id, version_id = _seed_calculation_flow(
        uow_factory, recorder, period_id=period_id
    )
    with uow_factory() as uow:
        rs = recorder.record_calculation_result_set(
            uow,
            RecordCalculationResultSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_execution_id=_create_execution(
                    uow, recorder, run, method_id, version_id, period_id
                ).calculation_execution_id,
                items=[
                    ResultItemInput(
                        result_type=CalculationResultType.OTHER,
                        result_name="m",
                        result_value=Decimal("1"),
                        result_unit="u",
                    )
                ],
                reporting_period_id=period_id,
                result_scope=ResultScope.MONTHLY,
                consolidation_type=ConsolidationType.DIRECT,
            ),
        )
        uow.commit()
    assert rs.reporting_period_id == period_id
    assert rs.consolidation_type is ConsolidationType.DIRECT


def test_annual_result_set_with_reporting_period(uow_factory, recorder) -> None:
    period_id = _create_annual_period(uow_factory, recorder).reporting_period_id
    run, agent_id, method_id, version_id = _seed_calculation_flow(
        uow_factory, recorder, period_id=period_id
    )
    with uow_factory() as uow:
        rs = recorder.record_calculation_result_set(
            uow,
            RecordCalculationResultSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_execution_id=_create_execution(
                    uow, recorder, run, method_id, version_id, period_id
                ).calculation_execution_id,
                items=[
                    ResultItemInput(
                        result_type=CalculationResultType.OTHER,
                        result_name="a",
                        result_value=Decimal("12"),
                        result_unit="u",
                    )
                ],
                reporting_period_id=period_id,
                result_scope=ResultScope.ANNUAL,
                consolidation_type=ConsolidationType.MONTHLY_TO_ANNUAL,
            ),
        )
        uow.commit()
    assert rs.result_scope is ResultScope.ANNUAL
    assert rs.consolidation_type is ConsolidationType.MONTHLY_TO_ANNUAL


# ---- Aggregation links ----


def test_aggregation_links_monthly_to_annual_and_daily_to_monthly(
    uow_factory, recorder
) -> None:
    monthly_period = _create_monthly_period(uow_factory, recorder)
    annual_period = _create_annual_period(uow_factory, recorder)
    daily_period = _create_daily_period(uow_factory, recorder)
    run, agent_id, method_id, version_id = _seed_calculation_flow(uow_factory, recorder)

    with uow_factory() as uow:
        daily_rs = recorder.record_calculation_result_set(
            uow,
            RecordCalculationResultSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_execution_id=_create_execution(
                    uow, recorder, run, method_id, version_id, daily_period.reporting_period_id
                ).calculation_execution_id,
                items=[
                    ResultItemInput(
                        result_type=CalculationResultType.OTHER,
                        result_name="d",
                        result_value=Decimal("1"),
                        result_unit="u",
                    )
                ],
                reporting_period_id=daily_period.reporting_period_id,
                result_scope=ResultScope.DAILY,
            ),
        )
        monthly_rs = recorder.record_calculation_result_set(
            uow,
            RecordCalculationResultSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_execution_id=_create_execution(
                    uow, recorder, run, method_id, version_id, monthly_period.reporting_period_id
                ).calculation_execution_id,
                items=[
                    ResultItemInput(
                        result_type=CalculationResultType.OTHER,
                        result_name="m",
                        result_value=Decimal("31"),
                        result_unit="u",
                    )
                ],
                reporting_period_id=monthly_period.reporting_period_id,
                result_scope=ResultScope.MONTHLY,
            ),
        )
        annual_rs = recorder.record_calculation_result_set(
            uow,
            RecordCalculationResultSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_execution_id=_create_execution(
                    uow, recorder, run, method_id, version_id, annual_period.reporting_period_id
                ).calculation_execution_id,
                items=[
                    ResultItemInput(
                        result_type=CalculationResultType.OTHER,
                        result_name="a",
                        result_value=Decimal("365"),
                        result_unit="u",
                    )
                ],
                reporting_period_id=annual_period.reporting_period_id,
                result_scope=ResultScope.ANNUAL,
            ),
        )
        recorder.record_result_aggregation_link(
            uow,
            RecordResultAggregationLinkCommand(
                parent_result_set_id=monthly_rs.calculation_result_set_id,
                child_result_set_id=daily_rs.calculation_result_set_id,
                aggregation_type=AggregationType.DAILY_TO_MONTHLY,
                parent_period_id=monthly_period.reporting_period_id,
                child_period_id=daily_period.reporting_period_id,
            ),
        )
        recorder.record_result_aggregation_link(
            uow,
            RecordResultAggregationLinkCommand(
                parent_result_set_id=annual_rs.calculation_result_set_id,
                child_result_set_id=monthly_rs.calculation_result_set_id,
                aggregation_type=AggregationType.MONTHLY_TO_ANNUAL,
                parent_period_id=annual_period.reporting_period_id,
                child_period_id=monthly_period.reporting_period_id,
            ),
        )
        uow.commit()

    with uow_factory() as uow2:
        annual_children = uow2.result_aggregation_links.list_children(
            annual_rs.calculation_result_set_id
        )
        monthly_parents = uow2.result_aggregation_links.list_parents(
            monthly_rs.calculation_result_set_id
        )
    assert len(annual_children) == 1
    assert annual_children[0].child_result_set_id == monthly_rs.calculation_result_set_id
    assert len(monthly_parents) == 1
    assert monthly_parents[0].parent_result_set_id == annual_rs.calculation_result_set_id


# ---- Hash ----


def test_hash_record_stores_canonicalization_and_scope(uow_factory, recorder) -> None:
    run, _, _, _ = _seed_calculation_flow(uow_factory, recorder)
    with uow_factory() as uow:
        artifact = uow.source_artifacts.list_by_pipeline_run(run.pipeline_run_id)
        assert artifact
        hashes = uow.hash_records.list_by_pipeline_run(run.pipeline_run_id)
    assert hashes
    hr = hashes[0]
    assert hr.canonicalization_method == "prov_canonical_v1"
    assert hr.hash_scope is not None


def test_hash_record_backward_compatible_nullable_fields(uow_factory, recorder) -> None:
    from provenance_service.domain.audit.entities import HashRecord
    from provenance_service.domain.shared.enums import HashAlgorithm, HashSubjectKind

    run, _, _, _ = _seed_calculation_flow(uow_factory, recorder)
    subject_id = new_uuid7()
    hash_record_id = new_uuid7()
    with uow_factory() as uow:
        uow.hash_records.add(
            HashRecord(
                hash_record_id=hash_record_id,
                pipeline_run_id=run.pipeline_run_id,
                subject_kind=HashSubjectKind.OTHER,
                subject_id=subject_id,
                hash_algorithm=HashAlgorithm.SHA256,
                hash_value="c" * 64,
                computed_at=datetime.now(timezone.utc),
            )
        )
        uow.commit()
    with uow_factory() as uow2:
        row = uow2.hash_records.get(hash_record_id)
    assert row is not None
    assert row.hash_scope is None


# ---- Append-only ----


def test_calculation_parameter_value_blocks_update(engine, uow_factory, recorder) -> None:
    run, agent_id, method_id, version_id = _seed_calculation_flow(uow_factory, recorder)
    param_value_id = new_uuid7()
    with uow_factory() as uow:
        execution = _create_execution(uow, recorder, run, method_id, version_id, None)
        param_set = recorder.record_calculation_parameter_set(
            uow,
            RecordCalculationParameterSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_method_version_id=version_id,
                values=[
                    ParameterValueInput(
                        parameter_name="factor",
                        parameter_value_numeric=Decimal("1.5"),
                    )
                ],
                parameter_set_status=ParameterSetStatus.LOCKED,
            ),
        )
        uow.commit()

    tbl = CalculationParameterValueModel.__tablename__
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT calculation_parameter_value_id FROM {tbl} LIMIT 1")
        ).fetchone()
        assert row is not None
        with pytest.raises(DatabaseError):
            conn.execute(
                text(f"UPDATE {tbl} SET parameter_value_text = 'tampered' WHERE calculation_parameter_value_id = :id"),
                {"id": row[0]},
            )
            conn.commit()


def test_calculation_parameter_value_blocks_delete(engine, uow_factory, recorder) -> None:
    run, _, method_id, version_id = _seed_calculation_flow(uow_factory, recorder)
    with uow_factory() as uow:
        recorder.record_calculation_parameter_set(
            uow,
            RecordCalculationParameterSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_method_version_id=version_id,
                values=[ParameterValueInput(parameter_name="x", parameter_value_text="1")],
            ),
        )
        uow.commit()
    tbl = CalculationParameterValueModel.__tablename__
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT calculation_parameter_value_id FROM {tbl} LIMIT 1")
        ).fetchone()
        with pytest.raises(DatabaseError):
            conn.execute(
                text(f"DELETE FROM {tbl} WHERE calculation_parameter_value_id = :id"),
                {"id": row[0]},
            )
            conn.commit()


# ---- helpers ----


def _create_daily_period(uow_factory, recorder):
    with uow_factory() as uow:
        period = recorder.record_reporting_period(
            uow,
            RecordReportingPeriodCommand(
                period_start=_utc(2026, 1, 1),
                period_end=_utc(2026, 1, 2),
                period_granularity=PeriodGranularity.DAILY,
                year=2026,
                month=1,
                day=1,
                period_label=f"daily-{new_uuid7().hex[:6]}",
            ),
        )
        uow.commit()
    return period


def _create_monthly_period(uow_factory, recorder):
    with uow_factory() as uow:
        period = recorder.record_reporting_period(
            uow,
            RecordReportingPeriodCommand(
                period_start=_utc(2026, 1, 1),
                period_end=_utc(2026, 2, 1),
                period_granularity=PeriodGranularity.MONTHLY,
                year=2026,
                month=1,
                period_label=f"monthly-{new_uuid7().hex[:6]}",
            ),
        )
        uow.commit()
    return period


def _create_annual_period(uow_factory, recorder):
    with uow_factory() as uow:
        period = recorder.record_reporting_period(
            uow,
            RecordReportingPeriodCommand(
                period_start=_utc(2026, 1, 1),
                period_end=_utc(2027, 1, 1),
                period_granularity=PeriodGranularity.ANNUAL,
                year=2026,
                period_label=f"annual-{new_uuid7().hex[:6]}",
            ),
        )
        uow.commit()
    return period


def _create_execution(uow, recorder, run, method_id, version_id, period_id):
    wrapper_execs = uow.wrapper_executions.list_by_pipeline_run(run.pipeline_run_id)
    assert wrapper_execs, "expected wrapper execution from seed flow"
    wrapper_exec = wrapper_execs[0]
    batch = recorder.record_normalized_batch(
        uow,
        RecordNormalizedBatchCommand(
            pipeline_run_id=run.pipeline_run_id,
            wrapper_execution_id=wrapper_exec.wrapper_execution_id,
            batch_code=f"batch-{new_uuid7().hex[:8]}",
            schema_version="1.0",
            record_count=1,
            content_hash="e" * 64,
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
            semantic_integration_execution_id=integration.semantic_integration_execution_id,
            graph_name="agrotrace:graph",
            snapshot_label=f"snap-{new_uuid7().hex[:8]}",
            payload={"items": [1]},
        ),
    )
    param_set = recorder.record_calculation_parameter_set(
        uow,
        RecordCalculationParameterSetCommand(
            pipeline_run_id=run.pipeline_run_id,
            calculation_method_version_id=version_id,
            values=[ParameterValueInput(parameter_name="p", parameter_value_numeric=Decimal("1"))],
        ),
    )
    return recorder.record_calculation_execution(
        uow,
        RecordCalculationExecutionCommand(
            pipeline_run_id=run.pipeline_run_id,
            canonical_snapshot_id=snapshot.canonical_snapshot_id,
            calculation_method_version_id=version_id,
            calculation_parameter_set_id=param_set.calculation_parameter_set_id,
            started_at=datetime.now(timezone.utc),
            execution_status=CalculationExecutionStatus.SUCCEEDED,
            reporting_period_id=period_id,
        ),
    )


def _create_preliminary_result(uow_factory, recorder, run, agent_id, method_id, version_id, period_id):
    with uow_factory() as uow:
        rs = recorder.record_calculation_result_set(
            uow,
            RecordCalculationResultSetCommand(
                pipeline_run_id=run.pipeline_run_id,
                calculation_execution_id=_create_execution(
                    uow, recorder, run, method_id, version_id, period_id
                ).calculation_execution_id,
                items=[
                    ResultItemInput(
                        result_type=CalculationResultType.GHG_EMISSION,
                        result_name="total",
                        result_value=Decimal("50"),
                        result_unit="kg",
                    )
                ],
                reporting_period_id=period_id,
                result_scope=ResultScope.MONTHLY,
                consolidation_type=ConsolidationType.DIRECT,
            ),
        )
        uow.commit()
    return rs.calculation_result_set_id
