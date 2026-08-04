"""Adapter para proveniência / traceability-service."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

import config
from services import direct_imports as di
from services.mock_data import mock_provenance_events
from utils.date_helpers import now_iso
from utils.pipeline_logging import log_call, log_fail, timed_op, truncate

logger = logging.getLogger("agrotrace.provenance")

_recorder: Any = None
_uow_factory: Any = None
_reviewer_agent_id: UUID | None = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _available() -> bool:
    return (
        config.USE_DIRECT_FUNCTION_CALLS
        and not config.USE_MOCK_DATA
        and di.ProvenanceRecorder is not None
        and di.get_uow_factory is not None
    )


def _get_recorder() -> Any:
    global _recorder, _uow_factory
    if _recorder is None:
        _recorder = di.ProvenanceRecorder()
        _uow_factory = di.get_uow_factory()
    return _recorder, _uow_factory


def _ensure_reviewer_agent() -> UUID:
    global _reviewer_agent_id
    if _reviewer_agent_id is not None:
        return _reviewer_agent_id

    from provenance_service.domain.prov_core.entities import ProvAgent
    from provenance_service.domain.shared.enums import ProvAgentType

    recorder, uow_factory = _get_recorder()
    external_ref = "frontend@agrotrace"

    # Reaproveita o agente já existente (persistido em execuções anteriores)
    with uow_factory() as uow:
        existing = uow.prov_agents.get_by_external_reference(external_ref)
        if existing is not None:
            _reviewer_agent_id = existing.agent_id
            return _reviewer_agent_id

    agent_id = uuid.uuid4()
    with uow_factory() as uow:
        uow.prov_agents.add(
            ProvAgent(
                agent_id=agent_id,
                agent_type=ProvAgentType.HUMAN,
                name="frontend-approver",
                external_reference=external_ref,
                created_at=_utc_now(),
            )
        )
        uow.commit()
    _reviewer_agent_id = agent_id
    return agent_id


def register_provenance_event(event_type: str, payload: dict) -> dict[str, Any]:
    """Registra evento observável na proveniência real ou mock."""
    if not _available():
        return {
            "source": "mock",
            "event_type": event_type,
            "payload": payload,
            "created_at": now_iso(),
            "status": "mocked",
        }

    try:
        recorder, uow_factory = _get_recorder()
        aggregate_id = uuid.UUID(payload.get("aggregate_id")) if payload.get("aggregate_id") else uuid.uuid4()
        with uow_factory() as uow:
            recorder.record_observable_event(
                uow,
                event_type=event_type,
                aggregate_type=payload.get("aggregate_type", "emission_cycle"),
                aggregate_id=aggregate_id,
                payload=payload,
                pipeline_run_id=UUID(payload["pipeline_run_id"]) if payload.get("pipeline_run_id") else None,
                calculation_execution_id=UUID(payload["calculation_execution_id"]) if payload.get("calculation_execution_id") else None,
                calculation_result_set_id=UUID(payload["calculation_result_set_id"]) if payload.get("calculation_result_set_id") else None,
                reporting_period_id=UUID(payload["reporting_period_id"]) if payload.get("reporting_period_id") else None,
            )
            uow.commit()
        return {"source": "real", "event_type": event_type, "aggregate_id": str(aggregate_id), "created_at": now_iso()}
    except Exception as exc:
        log_fail(
            logger,
            "provenance.emit.failed",
            event_type=event_type,
            cycle_id=payload.get("cycle_id"),
            pipeline_run_id=payload.get("pipeline_run_id"),
            error=str(exc),
        )
        return {"source": "mock", "event_type": event_type, "error": str(exc), "created_at": now_iso()}


def start_pipeline_run(farm_ref: str, period_ref: str, run_code: str) -> dict[str, Any]:
    if not _available():
        out = {"source": "mock", "pipeline_run_id": str(uuid.uuid4()), "run_code": run_code, "mode": "mock"}
        log_call(
            logger,
            "provenance.start_run",
            mode="mock",
            property_id=farm_ref,
            period=period_ref,
            run_code=run_code,
            pipeline_run_id=truncate(out["pipeline_run_id"]),
        )
        return out

    from provenance_service.domain.shared.enums import RunType

    log_call(logger, "provenance.start_run.start", property_id=farm_ref, period=period_ref, run_code=run_code)
    with timed_op() as timer:
        recorder, uow_factory = _get_recorder()
        with uow_factory() as uow:
            run = recorder.start_pipeline_run(
                uow,
                di.StartPipelineRunCommand(
                    run_code=run_code,
                    farm_reference=farm_ref,
                    reporting_period_reference=period_ref,
                    run_type=RunType.MONTHLY_CALCULATION,
                    idempotency_key=run_code,
                ),
            )
            uow.commit()
        out = {"source": "real", "pipeline_run_id": str(run.pipeline_run_id), "run_code": run.run_code, "mode": "real"}
        log_call(
            logger,
            "provenance.start_run.done",
            mode="real",
            property_id=farm_ref,
            period=period_ref,
            pipeline_run_id=truncate(out["pipeline_run_id"]),
            duration_ms=timer.duration_ms,
        )
    return out


def record_reporting_period(year: int, month: int, label: str) -> dict[str, Any]:
    if not _available():
        return {"source": "mock", "reporting_period_id": str(uuid.uuid4()), "period_label": label}

    from provenance_service.domain.shared.enums import PeriodGranularity

    recorder, uow_factory = _get_recorder()
    with uow_factory() as uow:
        period = recorder.record_reporting_period(
            uow,
            di.RecordReportingPeriodCommand(
                period_start=datetime(year, month, 1, tzinfo=timezone.utc),
                period_end=datetime(year, month + 1 if month < 12 else 1, 1, tzinfo=timezone.utc),
                period_granularity=PeriodGranularity.MONTHLY,
                year=year,
                month=month,
                period_label=label,
            ),
        )
        uow.commit()
    return {"source": "real", "reporting_period_id": str(period.reporting_period_id), "period_label": label}


def record_source_artifact(pipeline_run_id: str, raw_meta: dict) -> dict[str, Any]:
    if not _available():
        return {"source": "mock", "source_artifact_id": str(uuid.uuid4())}

    recorder, uow_factory = _get_recorder()
    with uow_factory() as uow:
        artifact = recorder.record_source_artifact(
            uow,
            di.RecordSourceArtifactCommand(
                pipeline_run_id=UUID(pipeline_run_id),
                source_system="frontend-upload",
                original_filename=raw_meta["original_filename"],
                storage_uri=raw_meta["stored_path"],
                content_hash=raw_meta["sha256"],
                file_size_bytes=raw_meta.get("file_size_bytes"),
                received_at=_utc_now(),
            ),
        )
        uow.commit()
    return {"source": "real", "source_artifact_id": str(artifact.source_artifact_id)}


def record_wrapper_flow(
    pipeline_run_id: str,
    raw_meta: dict,
    wrapper_result: dict,
    *,
    source_artifact_id: str | None = None,
) -> dict[str, Any]:
    if not _available():
        return {
            "source": "mock",
            "wrapper_definition_id": str(uuid.uuid4()),
            "wrapper_execution_id": str(uuid.uuid4()),
            "normalized_batch_id": str(uuid.uuid4()),
        }

    from provenance_service.domain.shared.enums import WrapperExecutionStatus

    recorder, uow_factory = _get_recorder()
    artifact_id = source_artifact_id
    if not artifact_id:
        artifact_id = record_source_artifact(pipeline_run_id, raw_meta)["source_artifact_id"]

    with uow_factory() as uow:
        wrapper_def = recorder.record_wrapper_definition(
            uow,
            di.RecordWrapperDefinitionCommand(
                wrapper_name="agrotrace-wrapper",
                wrapper_version=wrapper_result.get("layout_version", "v1"),
                source_layout_name=wrapper_result.get("layout_id", "monthly:v1"),
            ),
        )
        execution = recorder.record_wrapper_execution(
            uow,
            di.RecordWrapperExecutionCommand(
                pipeline_run_id=UUID(pipeline_run_id),
                wrapper_definition_id=wrapper_def.wrapper_definition_id,
                input_artifact_id=UUID(artifact_id),
                started_at=_utc_now(),
                execution_status=WrapperExecutionStatus.SUCCEEDED,
                execution_payload_hash=wrapper_result.get("content_hash"),
            ),
        )
        batch = recorder.record_normalized_batch(
            uow,
            di.RecordNormalizedBatchCommand(
                pipeline_run_id=UUID(pipeline_run_id),
                wrapper_execution_id=execution.wrapper_execution_id,
                batch_code=f"batch-{uuid.uuid4().hex[:8]}",
                schema_version="1.0",
                record_count=wrapper_result.get("rows_valid", 0),
                content_hash=wrapper_result.get("content_hash"),
                storage_uri=wrapper_result.get("normalized_file"),
            ),
        )
        uow.commit()

    return {
        "source": "real",
        "wrapper_definition_id": str(wrapper_def.wrapper_definition_id),
        "wrapper_execution_id": str(execution.wrapper_execution_id),
        "normalized_batch_id": str(batch.normalized_batch_id),
    }


def record_semantic_and_canonical(pipeline_run_id: str, normalized_batch_id: str, ontology_result: dict) -> dict[str, Any]:
    if not _available():
        return {
            "source": "mock",
            "semantic_integration_id": str(uuid.uuid4()),
            "canonical_snapshot_id": str(uuid.uuid4()),
        }

    from provenance_service.domain.shared.enums import SemanticExecutionStatus

    recorder, uow_factory = _get_recorder()
    with uow_factory() as uow:
        integration = recorder.record_semantic_integration(
            uow,
            di.RecordSemanticIntegrationCommand(
                pipeline_run_id=UUID(pipeline_run_id),
                normalized_batch_id=UUID(normalized_batch_id),
                ontology_name="agromrv-lite",
                ontology_version=ontology_result.get("ontology_version", "2026.01"),
                mapping_rule_version=ontology_result.get("mapping_version", "1.0"),
                started_at=_utc_now(),
                execution_status=SemanticExecutionStatus.SUCCEEDED,
                triples_generated=ontology_result.get("relationships_created", 0),
            ),
        )
        snapshot = recorder.record_canonical_snapshot(
            uow,
            di.RecordCanonicalSnapshotCommand(
                pipeline_run_id=UUID(pipeline_run_id),
                semantic_integration_execution_id=integration.semantic_integration_execution_id,
                graph_name="agrotrace:canonical",
                snapshot_label=f"snap-{uuid.uuid4().hex[:8]}",
                payload={"entities": ontology_result.get("entities_created", 0)},
                snapshot_hash_override=ontology_result.get("ontology_hash"),
            ),
        )
        uow.commit()

    return {
        "source": "real",
        "semantic_integration_id": str(integration.semantic_integration_execution_id),
        "canonical_snapshot_id": str(snapshot.canonical_snapshot_id),
    }


def _parameter_values_from_calculation_result(calculation_result: dict) -> list:
    """Converte factors_used do resultado em ParameterValueInput para proveniência."""
    if di.ParameterValueInput is None:
        return []

    factors = calculation_result.get("factors_used") or {}
    values: list = []

    gwp = factors.get("gwp") or calculation_result.get("gwp") or {}
    if gwp.get("CH4") is not None:
        values.append(di.ParameterValueInput(
            parameter_name="gwp_ch4", parameter_value_numeric=Decimal(str(gwp["CH4"]))
        ))
    if gwp.get("N2O") is not None:
        values.append(di.ParameterValueInput(
            parameter_name="gwp_n2o", parameter_value_numeric=Decimal(str(gwp["N2O"]))
        ))

    for cat, val in (factors.get("enteric_ch4_kg_per_animal") or {}).items():
        values.append(di.ParameterValueInput(
            parameter_name=f"enteric_ch4_{cat}",
            parameter_value_numeric=Decimal(str(val)),
        ))

    for cat, val in (factors.get("manure_kg_per_kg_bw_per_day") or {}).items():
        values.append(di.ParameterValueInput(
            parameter_name=f"manure_kg_bw_day_{cat}",
            parameter_value_numeric=Decimal(str(val)),
        ))

    for cat, val in (factors.get("manure_ch4_kg_per_kg_manure") or {}).items():
        values.append(di.ParameterValueInput(
            parameter_name=f"manure_ch4_ef_{cat}",
            parameter_value_numeric=Decimal(str(val)),
        ))

    for vec, val in (factors.get("energy_co2_kg_per_unit") or {}).items():
        values.append(di.ParameterValueInput(
            parameter_name=f"energy_co2_{vec}",
            parameter_value_numeric=Decimal(str(val)),
        ))

    fert = factors.get("fertilizer_factors") or {}
    for key, val in fert.items():
        values.append(di.ParameterValueInput(
            parameter_name=f"fertilizer_{key}",
            parameter_value_numeric=Decimal(str(val)),
        ))

    if not values:
        values.append(di.ParameterValueInput(
            parameter_name="gwp_ch4", parameter_value_numeric=Decimal("25")
        ))

    return values


def record_calculation_flow(
    pipeline_run_id: str,
    canonical_snapshot_id: str,
    reporting_period_id: str,
    calculation_result: dict,
) -> dict[str, Any]:
    if not _available():
        return {
            "source": "mock",
            "calculation_execution_id": str(uuid.uuid4()),
            "calculation_result_set_id": str(uuid.uuid4()),
        }

    from provenance_service.domain.shared.enums import (
        CalculationExecutionStatus,
        CalculationResultType,
        ConsolidationType,
        ResultScope,
    )

    recorder, uow_factory = _get_recorder()
    method_info = calculation_result.get("method") or {}
    method_code = method_info.get("code") or "ECOFARM-T1-DAIRY"
    version_label = method_info.get("version") or "1.0.0"
    method_name = f"AgroTrace {method_code}"

    with uow_factory() as uow:
        recorder.record_calculation_method(
            uow, di.RecordCalculationMethodCommand(method_code=method_code, method_name=method_name)
        )
        uow.commit()

    with uow_factory() as uow:
        method = uow.calculation_methods.get_by_code(method_code)
        assert method is not None
        existing_versions = uow.calculation_method_versions.list_by_method(method.calculation_method_id)
        version = next((v for v in existing_versions if v.version_label == version_label), None)
        if version is None:
            version = recorder.record_calculation_method_version(
                uow,
                di.RecordCalculationMethodVersionCommand(
                    calculation_method_id=method.calculation_method_id,
                    version_label=version_label,
                ),
            )
        param_values = _parameter_values_from_calculation_result(calculation_result)
        param_set = recorder.record_calculation_parameter_set(
            uow,
            di.RecordCalculationParameterSetCommand(
                pipeline_run_id=UUID(pipeline_run_id),
                calculation_method_version_id=version.calculation_method_version_id,
                values=param_values,
            ),
        )
        execution = recorder.record_calculation_execution(
            uow,
            di.RecordCalculationExecutionCommand(
                pipeline_run_id=UUID(pipeline_run_id),
                canonical_snapshot_id=UUID(canonical_snapshot_id),
                calculation_method_version_id=version.calculation_method_version_id,
                calculation_parameter_set_id=param_set.calculation_parameter_set_id,
                started_at=_utc_now(),
                execution_status=CalculationExecutionStatus.SUCCEEDED,
                reporting_period_id=UUID(reporting_period_id),
            ),
        )
        result_set = recorder.record_calculation_result_set(
            uow,
            di.RecordCalculationResultSetCommand(
                pipeline_run_id=UUID(pipeline_run_id),
                calculation_execution_id=execution.calculation_execution_id,
                items=[
                    di.ResultItemInput(
                        result_type=CalculationResultType.GHG_EMISSION,
                        result_name="co2e_total_kg",
                        result_value=Decimal(str(calculation_result.get("co2e_total_kg", 0))),
                        result_unit="kg CO2e",
                    )
                ],
                reporting_period_id=UUID(reporting_period_id),
                result_scope=ResultScope.MONTHLY,
                consolidation_type=ConsolidationType.DIRECT,
                summary_hash_override=calculation_result.get("preliminary_hash"),
            ),
        )
        uow.commit()

    return {
        "source": "real",
        "calculation_execution_id": str(execution.calculation_execution_id),
        "calculation_result_set_id": str(result_set.calculation_result_set_id),
    }


def record_review_request(
    pipeline_run_id: str,
    result_set_id: str,
    reporting_period_id: str,
) -> dict[str, Any]:
    """Registra solicitação de revisão humana sem decisão (estado pendente)."""
    if not _available():
        return {"source": "mock", "decision": "pending"}

    from provenance_service.domain.shared.enums import CalculationReviewDecision

    recorder, uow_factory = _get_recorder()
    with uow_factory() as uow:
        review = recorder.record_calculation_review(
            uow,
            di.RecordCalculationReviewCommand(
                pipeline_run_id=UUID(pipeline_run_id),
                calculation_result_set_id=UUID(result_set_id),
                reviewer_agent_id=_ensure_reviewer_agent(),
                decision=CalculationReviewDecision.PENDING,
                review_comment="Aguardando revisão humana.",
                reporting_period_id=UUID(reporting_period_id),
            ),
        )
        uow.commit()
    return {"source": "real", "calculation_review_id": str(review.calculation_review_id), "decision": "pending"}


def record_approval(pipeline_run_id: str, result_set_id: str, reporting_period_id: str, approval: dict) -> dict[str, Any]:
    if not _available():
        return {"source": "mock", "decision": approval.get("decision", "APPROVED")}

    from provenance_service.domain.shared.enums import CalculationReviewDecision

    recorder, uow_factory = _get_recorder()
    decision_map = {
        "APPROVED": CalculationReviewDecision.APPROVED,
        "REJECTED": CalculationReviewDecision.REJECTED,
        "CORRECTION_REQUESTED": CalculationReviewDecision.CHANGES_REQUESTED,
    }
    with uow_factory() as uow:
        review = recorder.record_calculation_review(
            uow,
            di.RecordCalculationReviewCommand(
                pipeline_run_id=UUID(pipeline_run_id),
                calculation_result_set_id=UUID(result_set_id),
                reviewer_agent_id=_ensure_reviewer_agent(),
                decision=decision_map.get(approval.get("decision", "APPROVED"), CalculationReviewDecision.APPROVED),
                review_comment=approval.get("justification"),
                reporting_period_id=UUID(reporting_period_id),
            ),
        )
        uow.commit()
    return {"source": "real", "calculation_review_id": str(review.calculation_review_id)}


def record_publication(pipeline_run_id: str, result_set_id: str, publication: dict) -> dict[str, Any]:
    if not _available():
        return {"source": "mock", "publication_status": "PUBLISHED"}

    from provenance_service.domain.shared.enums import ResultPublicationStatus

    recorder, uow_factory = _get_recorder()
    with uow_factory() as uow:
        pub = recorder.record_result_publication(
            uow,
            di.RecordResultPublicationCommand(
                pipeline_run_id=UUID(pipeline_run_id),
                calculation_result_set_id=UUID(result_set_id),
                target_graph_name="agrotrace:final",
                ontology_name="agromrv-lite",
                ontology_version=publication.get("ontology_version", "final_v1"),
                publication_status=ResultPublicationStatus.PUBLISHED,
                publication_payload_hash=publication.get("ontology_hash"),
            ),
        )
        uow.commit()
    return {"source": "real", "result_publication_id": str(pub.result_publication_execution_id)}


def list_outbox_events(limit: int = 100) -> list[dict[str, Any]]:
    if not _available() or di.ListOutboxEvents is None:
        return mock_provenance_events("demo")

    try:
        _, uow_factory = _get_recorder()
        use_case = di.ListOutboxEvents(uow_factory)
        result = use_case.execute(di.ListOutboxEventsQuery(limit=limit, offset=0))
        events = []
        for e in result.items:
            events.append({
                "event_id": str(e.outbox_event_id),
                "event_type": e.event_type,
                "aggregate_id": str(e.aggregate_id),
                "pipeline_execution_id": str(e.pipeline_run_id) if e.pipeline_run_id else None,
                "calculation_execution_id": str(e.calculation_execution_id) if e.calculation_execution_id else None,
                "reporting_period_id": str(e.reporting_period_id) if e.reporting_period_id else None,
                "payload_json": e.payload,
                "status": str(e.status.value if hasattr(e.status, "value") else e.status),
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "source_service": "provenance_service",
            })
        return events
    except Exception as exc:
        logger.warning("List outbox falhou: %s", exc)
        return mock_provenance_events("demo")


def build_event_table_rows(events: list[dict]) -> list[dict]:
    """Projeta eventos do outbox para colunas da tabela de proveniência."""
    from services.cycle_state import step_label_for_event

    return [
        {
            "evento": e.get("event_type"),
            "etapa": step_label_for_event(e.get("event_type", "")),
            "serviço": e.get("source_service", "provenance_service"),
            "status": e.get("status"),
            "data": e.get("created_at", "—"),
        }
        for e in events
    ]


def list_events_for_context(
    global_filter: dict,
    all_cycles: list[dict],
    active_cycle: dict,
    *,
    limit: int = 200,
    context_cycle_id: str | None = None,
    prov_cycle_id: str | None = None,
    cycles_in_context: list[dict] | None = None,
) -> list[dict]:
    """Lista eventos filtrados pelo contexto global e opcionalmente por ciclo."""
    from utils.file_helpers import get_cycle
    from utils.global_filter import filter_events_by_context
    from services.cycle_state import events_for_cycle

    events = list_outbox_events(limit=limit)
    events = filter_events_by_context(events, all_cycles, global_filter, active_cycle)

    cycle_id = active_cycle.get("cycle_id") or (global_filter or {}).get("cycle_id") or prov_cycle_id or context_cycle_id or ""
    if cycle_id and cycles_in_context:
        ids = {c.get("cycle_id") for c in cycles_in_context}
        if cycle_id not in ids:
            cycle_id = active_cycle.get("cycle_id") or ""
        if cycle_id in ids:
            ref_cycle = get_cycle(cycle_id) or active_cycle
            narrowed = events_for_cycle(events, cycle_id, ref_cycle)
            if narrowed:
                events = narrowed
    return events
