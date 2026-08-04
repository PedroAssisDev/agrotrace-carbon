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

    catalog = ontology_result.get("factor_catalog") or {}
    catalog_meta = {
        "version": catalog.get("_version"),
        "source": catalog.get("_source"),
        "groups": [k for k in catalog if not str(k).startswith("_")],
        "pending_count": sum(
            1
            for g in (catalog.get("_statuses") or {}).values()
            if isinstance(g, dict)
            for s in g.values()
            if str(s) == "pending"
        ),
    }

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
                payload={
                    "entities": ontology_result.get("entities_created", 0),
                    "factor_catalog": catalog_meta,
                },
                snapshot_hash_override=ontology_result.get("ontology_hash"),
            ),
        )
        uow.commit()

    return {
        "source": "real",
        "semantic_integration_id": str(integration.semantic_integration_execution_id),
        "canonical_snapshot_id": str(snapshot.canonical_snapshot_id),
        "factor_catalog": catalog_meta,
    }


def record_factor_catalog_materialization(
    pipeline_run_id: str,
    cycle: dict,
    catalog: dict,
) -> dict[str, Any]:
    """Registra materialização do catálogo (evento observável + trilha no ciclo)."""
    statuses = catalog.get("_statuses") or {}
    pending_count = sum(
        1
        for g in statuses.values()
        if isinstance(g, dict)
        for s in g.values()
        if str(s) == "pending"
    )
    payload = {
        "aggregate_type": "emission_cycle",
        "aggregate_id": cycle.get("cycle_id"),
        "pipeline_run_id": pipeline_run_id,
        "event": "factor_catalog_materialized",
        "version": catalog.get("_version"),
        "source": catalog.get("_source"),
        "pending_count": pending_count,
        "groups": [k for k in catalog if not str(k).startswith("_")],
        "cycle_events": (cycle.get("ontology_parameter_events") or [])[-3:],
    }
    return register_provenance_event("FACTOR_CATALOG_MATERIALIZED", payload)


def _parameter_values_from_calculation_result(calculation_result: dict) -> list:
    """Converte explanation/factors_used do resultado em ParameterValueInput para proveniência."""
    if di.ParameterValueInput is None:
        return []

    explanation = calculation_result.get("explanation") or {}
    factors = calculation_result.get("factors_used") or {}
    if not factors and explanation:
        # Deriva factors_used da explanation quando ausente
        try:
            from services.calculation_explanation_service import applied_factors_from_explanation

            factors = {
                "enteric_ch4_kg_per_animal": applied_factors_from_explanation(explanation, "enteric_ch4_kg_per_animal"),
                "manure_kg_per_kg_bw_per_day": applied_factors_from_explanation(explanation, "manure_kg_per_kg_bw_per_day"),
                "manure_ch4_kg_per_kg_manure": applied_factors_from_explanation(explanation, "manure_ch4_kg_per_kg_manure"),
                "energy_co2_kg_per_unit": applied_factors_from_explanation(explanation, "energy_co2_kg_per_unit"),
                "fertilizer_factors": applied_factors_from_explanation(explanation, "fertilizer_factors"),
                "gwp": applied_factors_from_explanation(explanation, "gwp"),
            }
        except Exception:
            pass

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

    # Sem inventar GWP fictício — lista vazia é válida (parâmetros ausentes).
    return values


def record_calculation_flow(
    pipeline_run_id: str,
    canonical_snapshot_id: str,
    reporting_period_id: str,
    calculation_result: dict,
    *,
    supersedes_id: str | None = None,
    correction_reason: str | None = None,
) -> dict[str, Any]:
    if not _available():
        mock_id = str(uuid.uuid4())
        return {
            "source": "mock",
            "calculation_execution_id": str(uuid.uuid4()),
            "calculation_result_set_id": mock_id,
            "prov_entity_id": str(uuid.uuid4()),
            "supersedes_id": supersedes_id,
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
    supersedes_uuid = UUID(str(supersedes_id)) if supersedes_id else None

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
        meta: dict[str, Any] = {}
        if correction_reason:
            meta["correction_reason"] = correction_reason
        if supersedes_id:
            meta["supersedes_id"] = str(supersedes_id)
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
                supersedes_id=supersedes_uuid,
                correction_reason=correction_reason,
                metadata=meta,
            ),
        )
        if supersedes_uuid is not None:
            try:
                uow.calculation_result_sets.mark_superseded(
                    supersedes_uuid, result_set.calculation_result_set_id
                )
            except Exception as exc:
                logger.warning("mark_superseded falhou: %s", exc)
        uow.commit()

    return {
        "source": "real",
        "calculation_execution_id": str(execution.calculation_execution_id),
        "calculation_result_set_id": str(result_set.calculation_result_set_id),
        "prov_entity_id": str(result_set.prov_entity_id),
        "supersedes_id": str(supersedes_uuid) if supersedes_uuid else None,
    }


def record_correction_request(cycle: dict, correction: dict) -> dict[str, Any]:
    """Registra atividade de solicitação de correção (CHANGES_REQUESTED) na proveniência."""
    if not _available():
        return {"source": "mock", "decision": "changes_requested", "correction_id": correction.get("correction_id")}

    pipeline_run_id = cycle.get("pipeline_run_id")
    result_set_id = (
        correction.get("source_result_set_id")
        or cycle.get("calculation_result_set_id")
    )
    reporting_period_id = cycle.get("reporting_period_id")
    if not (pipeline_run_id and result_set_id and reporting_period_id):
        return {
            "source": "unavailable",
            "reason": "missing_ids",
            "correction_id": correction.get("correction_id"),
        }

    from provenance_service.domain.shared.enums import CalculationReviewDecision

    recorder, uow_factory = _get_recorder()
    meta = {
        "correction_id": correction.get("correction_id"),
        "cycle_id": cycle.get("cycle_id"),
        "target": correction.get("target"),
        "correctable_fields": [
            f.get("field") for f in (correction.get("correctable_fields") or []) if isinstance(f, dict)
        ],
        "requested_by": correction.get("requested_by"),
        "requested_at": correction.get("requested_at"),
        "service": "frontend.result_correction_service",
    }
    with uow_factory() as uow:
        review = recorder.record_calculation_review(
            uow,
            di.RecordCalculationReviewCommand(
                pipeline_run_id=UUID(str(pipeline_run_id)),
                calculation_result_set_id=UUID(str(result_set_id)),
                reviewer_agent_id=_ensure_reviewer_agent(),
                decision=CalculationReviewDecision.CHANGES_REQUESTED,
                review_comment=correction.get("justification"),
                reporting_period_id=UUID(str(reporting_period_id)),
                metadata=meta,
            ),
        )
        uow.commit()
    return {
        "source": "real",
        "calculation_review_id": str(review.calculation_review_id),
        "decision": "changes_requested",
        "correction_id": correction.get("correction_id"),
    }


def record_result_revision(
    previous_result_set_id: str,
    new_result_set_id: str,
    reason: str | None = None,
    *,
    invalidate_previous: bool = False,
) -> dict[str, Any]:
    """Vincula entidades PROV via prov_core_prov_revision (wasRevisionOf)."""
    if not _available():
        return {"source": "mock", "previous": previous_result_set_id, "new": new_result_set_id}

    from provenance_service.application.services import RecordRevisionCommand

    recorder, uow_factory = _get_recorder()
    try:
        with uow_factory() as uow:
            prev_rs = uow.calculation_result_sets.get(UUID(str(previous_result_set_id)))
            new_rs = uow.calculation_result_sets.get(UUID(str(new_result_set_id)))
            if prev_rs is None or new_rs is None:
                return {
                    "source": "unavailable",
                    "reason": "result_set_not_found",
                    "previous": previous_result_set_id,
                    "new": new_result_set_id,
                }
            revision = recorder.record_revision(
                uow,
                RecordRevisionCommand(
                    previous_entity_id=prev_rs.prov_entity_id,
                    new_entity_id=new_rs.prov_entity_id,
                    revision_reason=reason or "correction_recalculation",
                    invalidate_previous=invalidate_previous,
                    metadata={
                        "previous_result_set_id": str(previous_result_set_id),
                        "new_result_set_id": str(new_result_set_id),
                    },
                ),
            )
            # wasDerivedFrom complementar
            try:
                from provenance_service.domain.prov_core.relations import ProvDerivedFrom
                from provenance_service.domain.shared.ids import new_uuid7

                uow.prov_relations.add_derived_from(
                    ProvDerivedFrom(
                        derived_id=new_uuid7(),
                        generated_entity_id=new_rs.prov_entity_id,
                        source_entity_id=prev_rs.prov_entity_id,
                        derivation_type="correction_recalculation",
                    )
                )
            except Exception as exc:
                logger.warning("add_derived_from falhou: %s", exc)
            uow.commit()
        return {
            "source": "real",
            "revision_id": str(getattr(revision, "revision_id", None) or getattr(revision, "prov_revision_id", "")),
            "previous_entity_id": str(prev_rs.prov_entity_id),
            "new_entity_id": str(new_rs.prov_entity_id),
            "previous_result_set_id": str(previous_result_set_id),
            "new_result_set_id": str(new_result_set_id),
        }
    except Exception as exc:
        logger.warning("record_result_revision falhou: %s", exc)
        return {"source": "unavailable", "error": str(exc)}


def list_result_revisions(pipeline_run_id: str | UUID) -> list[dict[str, Any]]:
    """Lista revisões PROV do pipeline_run (prov_core_prov_revision)."""
    if not _available():
        return []
    try:
        pid = UUID(str(pipeline_run_id))
    except (ValueError, TypeError):
        return []
    try:
        _, uow_factory = _get_recorder()
        with uow_factory() as uow:
            revisions = uow.prov_relations.list_revisions_for_pipeline_run(pid)
            out = []
            for rev in revisions:
                out.append({
                    "revision_id": str(getattr(rev, "revision_id", None) or getattr(rev, "prov_revision_id", "")),
                    "previous_entity_id": str(rev.previous_entity_id),
                    "new_entity_id": str(rev.new_entity_id),
                    "revision_reason": getattr(rev, "revision_reason", None),
                    "revised_at": rev.revised_at.isoformat() if getattr(rev, "revised_at", None) else None,
                    "metadata": getattr(rev, "metadata", None) or {},
                })
            return out
    except Exception as exc:
        logger.warning("list_result_revisions falhou: %s", exc)
        return []


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


# ── Espelho blockchain → proveniência (RF006 / RNF001) ───────────────────────

_PUBLIC_META_KEYS = frozenset({
    "cycle_id",
    "publication_id",
    "evidence_package_id",
    "network_code",
    "package_hash",
    "merkle_root",
    "request_id",
    "agent",
    "service",
    "contract_address",
    "receipt_status",
    "event_identifier",
    "chain_id",
    "block_number",
    "transaction_hash",
    "confirmed_at",
    "verified_at",
    "verification_id",
    "anchoring_kind",
})

_SECRET_KEY_FRAGMENTS = (
    "private_key",
    "privkey",
    "rpc",
    "token",
    "secret",
    "password",
    "api_key",
    "apikey",
)


def _public_metadata(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Whitelist de metadados públicos — nunca copia segredos/RPC/paths absolutos."""
    out: dict[str, Any] = {}
    for key, value in (raw or {}).items():
        lk = str(key).lower()
        if any(frag in lk for frag in _SECRET_KEY_FRAGMENTS):
            continue
        if key not in _PUBLIC_META_KEYS:
            continue
        if isinstance(value, str) and (":\\" in value or value.startswith("/")):
            # paths absolutos não entram no espelho
            continue
        out[key] = value
    return out


def _subject_uuid_from_package_id(package_id: str) -> UUID:
    try:
        return UUID(str(package_id))
    except (ValueError, TypeError):
        return uuid.uuid5(uuid.NAMESPACE_URL, f"agrotrace:evidence:{package_id}")


def _parse_pipeline_run_id(cycle: dict) -> UUID | None:
    raw = cycle.get("pipeline_run_id")
    if not raw:
        return None
    try:
        return UUID(str(raw))
    except (ValueError, TypeError):
        return None


def _anchor_mode_for_network(network: str | None, anchoring_kind: str | None = None) -> str:
    if anchoring_kind == "SIMULADA" or network in (None, "", "local_simulated"):
        return "local_simulation"
    if network and "sepolia" in str(network).lower():
        return "testnet"
    return "testnet"


def record_anchor_request(
    cycle: dict,
    evidence: dict | None = None,
    request_meta: dict | None = None,
) -> dict[str, Any]:
    """Registra solicitação PENDING em audit_blockchain_anchor (+ hash_record)."""
    evidence = evidence or cycle.get("evidence_package") or {}
    meta_in = dict(request_meta or {})
    if not _available():
        return {"source": "unavailable", "status": "skipped", "reason": "provenance_unavailable"}

    pipeline_run_id = _parse_pipeline_run_id(cycle)
    if pipeline_run_id is None:
        return {"source": "unavailable", "status": "skipped", "reason": "missing_pipeline_run_id"}

    package_id = str(evidence.get("evidence_package_id") or meta_in.get("evidence_package_id") or "")
    if not package_id:
        return {"source": "unavailable", "status": "skipped", "reason": "missing_evidence_package_id"}

    package_hash = evidence.get("package_hash") or meta_in.get("package_hash") or ""
    merkle_root = evidence.get("merkle_root") or meta_in.get("merkle_root")
    network = (
        meta_in.get("network_code")
        or evidence.get("network")
        or getattr(config, "BLOCKCHAIN_DEFAULT_NETWORK_CODE", "local_simulated")
    )
    request_id = str(meta_in.get("request_id") or evidence.get("anchor_request_id") or package_id)
    publication = cycle.get("publication") or {}
    publication_id = publication.get("publication_id") or meta_in.get("publication_id")

    public_meta = _public_metadata({
        "cycle_id": cycle.get("cycle_id"),
        "publication_id": publication_id,
        "evidence_package_id": package_id,
        "network_code": network,
        "package_hash": package_hash,
        "merkle_root": merkle_root,
        "request_id": request_id,
        "agent": meta_in.get("agent") or "frontend.local_orchestrator",
        "service": "frontend.provenance_adapter",
    })

    try:
        from provenance_service.domain.shared.enums import (
            BlockchainAnchorStatus,
            HashAlgorithm,
            HashSubjectKind,
        )

        recorder, uow_factory = _get_recorder()
        subject_id = _subject_uuid_from_package_id(package_id)
        hash_value = str(package_hash or merkle_root or ("0" * 64))

        with uow_factory() as uow:
            hash_record = recorder.record_hash(
                uow,
                di.RecordHashCommand(
                    pipeline_run_id=pipeline_run_id,
                    subject_kind=HashSubjectKind.BUNDLE,
                    subject_id=subject_id,
                    hash_value=hash_value[:128],
                    hash_algorithm=HashAlgorithm.SHA256,
                    metadata={"kind": "evidence_package", "evidence_package_id": package_id},
                ),
            )
            anchor = recorder.record_blockchain_anchor(
                uow,
                di.RecordBlockchainAnchorCommand(
                    pipeline_run_id=pipeline_run_id,
                    hash_record_id=hash_record.hash_record_id,
                    blockchain_network=str(network),
                    anchor_status=BlockchainAnchorStatus.PENDING,
                    merkle_root=str(merkle_root) if merkle_root else None,
                    evidence_package_external_id=package_id,
                    package_hash=str(package_hash) if package_hash else None,
                    anchor_provider="frontend",
                    anchor_mode=_anchor_mode_for_network(str(network)),
                    metadata=public_meta,
                ),
            )
            uow.commit()

        return {
            "source": "real",
            "blockchain_anchor_id": str(anchor.blockchain_anchor_id),
            "hash_record_id": str(hash_record.hash_record_id),
            "anchor_status": anchor.anchor_status.value,
            "request_id": request_id,
            "evidence_package_id": package_id,
        }
    except Exception as exc:
        logger.warning("record_anchor_request falhou: %s", exc)
        return {"source": "unavailable", "status": "error", "error": str(exc)}


def record_anchor_confirmation(cycle: dict, anchor_result: dict | None = None) -> dict[str, Any]:
    """Atualiza espelho para CONFIRMED com metadados públicos da transação."""
    anchor_result = anchor_result or cycle.get("anchoring") or {}
    if not _available():
        return {"source": "unavailable", "status": "skipped", "reason": "provenance_unavailable"}

    pipeline_run_id = _parse_pipeline_run_id(cycle)
    evidence = cycle.get("evidence_package") or {}
    package_id = str(
        evidence.get("evidence_package_id")
        or anchor_result.get("evidence_package_id")
        or ""
    )
    if not package_id:
        return {"source": "unavailable", "status": "skipped", "reason": "missing_evidence_package_id"}

    tx = anchor_result.get("transaction_id") or anchor_result.get("transaction_hash")
    confirmed_at = _utc_now()
    public_meta = _public_metadata({
        "cycle_id": cycle.get("cycle_id"),
        "publication_id": (cycle.get("publication") or {}).get("publication_id"),
        "evidence_package_id": package_id,
        "network_code": anchor_result.get("network"),
        "package_hash": anchor_result.get("package_hash") or evidence.get("package_hash"),
        "merkle_root": anchor_result.get("merkle_root") or evidence.get("merkle_root"),
        "contract_address": anchor_result.get("contract_address"),
        "receipt_status": str(anchor_result.get("receipt_status") or "1"),
        "event_identifier": anchor_result.get("event_identifier") or anchor_result.get("evidence_key"),
        "transaction_hash": tx,
        "chain_id": str(anchor_result.get("chain_id")) if anchor_result.get("chain_id") is not None else None,
        "block_number": str(anchor_result.get("block_number")) if anchor_result.get("block_number") is not None else None,
        "confirmed_at": confirmed_at.isoformat(),
        "anchoring_kind": anchor_result.get("anchoring_kind"),
        "agent": "frontend.local_orchestrator",
        "service": "frontend.provenance_adapter",
    })

    try:
        from provenance_service.domain.shared.enums import BlockchainAnchorStatus

        recorder, uow_factory = _get_recorder()
        with uow_factory() as uow:
            confirmed = recorder.confirm_blockchain_anchor(
                uow,
                di.ConfirmBlockchainAnchorCommand(
                    evidence_package_external_id=package_id,
                    pipeline_run_id=pipeline_run_id,
                    anchor_status=BlockchainAnchorStatus.CONFIRMED,
                    chain_id=str(anchor_result.get("chain_id")) if anchor_result.get("chain_id") is not None else None,
                    transaction_hash=str(tx) if tx else None,
                    block_number=str(anchor_result.get("block_number")) if anchor_result.get("block_number") is not None else None,
                    confirmations=1,
                    confirmed_at=confirmed_at,
                    verification_uri=anchor_result.get("explorer_url"),
                    metadata=public_meta,
                ),
            )
            uow.commit()
        return {
            "source": "real",
            "blockchain_anchor_id": str(confirmed.blockchain_anchor_id),
            "anchor_status": confirmed.anchor_status.value,
            "transaction_hash": confirmed.transaction_hash,
        }
    except Exception as exc:
        logger.warning("record_anchor_confirmation falhou: %s", exc)
        return {"source": "unavailable", "status": "error", "error": str(exc)}


def record_integrity_verification(cycle: dict, integrity_result: dict | None = None) -> dict[str, Any]:
    """Registra verificação em audit_event (subject=blockchain_anchor)."""
    integrity_result = integrity_result or cycle.get("integrity") or {}
    if not _available():
        return {"source": "unavailable", "status": "skipped", "reason": "provenance_unavailable"}

    pipeline_run_id = _parse_pipeline_run_id(cycle)
    if pipeline_run_id is None:
        return {"source": "unavailable", "status": "skipped", "reason": "missing_pipeline_run_id"}

    evidence = cycle.get("evidence_package") or {}
    package_id = str(evidence.get("evidence_package_id") or "")
    is_valid = bool(integrity_result.get("is_valid"))
    result = "match" if is_valid else "divergence"
    verification_id = str(
        integrity_result.get("verification_id")
        or f"verify:{package_id}:{result}:{integrity_result.get('final_status', '')}"
    )
    verified_at = _utc_now()

    local_values = {
        "package_hash": evidence.get("package_hash"),
        "merkle_root": evidence.get("merkle_root"),
    }
    recovered_values = {
        "package_hash": evidence.get("package_hash") if is_valid else integrity_result.get("details", {}).get("recovered_package_hash"),
        "merkle_root": evidence.get("merkle_root") if is_valid else integrity_result.get("details", {}).get("recovered_merkle_root"),
        "final_status": integrity_result.get("final_status"),
    }
    if not is_valid and integrity_result.get("rows"):
        recovered_values["divergent_rows"] = [
            {
                "artifact": r.get("artifact"),
                "anchored_hash": r.get("anchored_hash"),
                "recalculated_hash": r.get("recalculated_hash"),
                "status": r.get("status"),
            }
            for r in (integrity_result.get("rows") or [])[:20]
            if r.get("status") == "divergente"
        ]

    try:
        recorder, uow_factory = _get_recorder()
        with uow_factory() as uow:
            anchors = uow.blockchain_anchors.list_by_pipeline_run(pipeline_run_id)
            anchor = None
            for a in anchors:
                if a.evidence_package_external_id == package_id:
                    anchor = a
                    break
            if anchor is None and anchors:
                anchor = anchors[-1]
            if anchor is None:
                return {
                    "source": "unavailable",
                    "status": "skipped",
                    "reason": "no_blockchain_anchor_mirror",
                }

            event = recorder.record_integrity_verification(
                uow,
                di.RecordIntegrityVerificationCommand(
                    pipeline_run_id=pipeline_run_id,
                    blockchain_anchor_id=anchor.blockchain_anchor_id,
                    verification_id=verification_id,
                    result=result,
                    local_values=local_values,
                    recovered_values=recovered_values,
                    verified_at=verified_at,
                    metadata=_public_metadata({
                        "cycle_id": cycle.get("cycle_id"),
                        "publication_id": (cycle.get("publication") or {}).get("publication_id"),
                        "package_hash": evidence.get("package_hash"),
                        "merkle_root": evidence.get("merkle_root"),
                        "agent": "frontend.local_orchestrator",
                        "service": "frontend.provenance_adapter",
                    }),
                ),
            )
            uow.commit()
        return {
            "source": "real",
            "audit_event_id": str(event.audit_event_id),
            "verification_id": verification_id,
            "result": result,
            "blockchain_anchor_id": str(anchor.blockchain_anchor_id),
        }
    except Exception as exc:
        logger.warning("record_integrity_verification falhou: %s", exc)
        return {"source": "unavailable", "status": "error", "error": str(exc)}


def list_anchors_for_pipeline_run(pipeline_run_id: str | UUID) -> list[dict[str, Any]]:
    """Lista espelhos de ancoragem no provenance.db (nunca no blockchain SQLite)."""
    if not _available():
        return []
    try:
        pid = UUID(str(pipeline_run_id))
    except (ValueError, TypeError):
        return []
    try:
        _, uow_factory = _get_recorder()
        with uow_factory() as uow:
            anchors = uow.blockchain_anchors.list_by_pipeline_run(pid)
            return [
                {
                    "blockchain_anchor_id": str(a.blockchain_anchor_id),
                    "pipeline_run_id": str(a.pipeline_run_id),
                    "hash_record_id": str(a.hash_record_id),
                    "blockchain_network": a.blockchain_network,
                    "chain_id": a.chain_id,
                    "transaction_hash": a.transaction_hash,
                    "block_number": a.block_number,
                    "anchor_status": a.anchor_status.value if hasattr(a.anchor_status, "value") else str(a.anchor_status),
                    "merkle_root": a.merkle_root,
                    "package_hash": a.package_hash,
                    "evidence_package_external_id": a.evidence_package_external_id,
                    "anchor_provider": a.anchor_provider,
                    "anchor_mode": a.anchor_mode,
                    "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
                    "confirmed_at": a.confirmed_at.isoformat() if a.confirmed_at else None,
                    "verification_uri": a.verification_uri,
                    "metadata": _public_metadata(a.metadata or {}),
                }
                for a in anchors
            ]
    except Exception as exc:
        logger.warning("list_anchors_for_pipeline_run falhou: %s", exc)
        return []


def list_audit_events_for_anchor(blockchain_anchor_id: str | UUID) -> list[dict[str, Any]]:
    if not _available():
        return []
    try:
        aid = UUID(str(blockchain_anchor_id))
    except (ValueError, TypeError):
        return []
    try:
        _, uow_factory = _get_recorder()
        with uow_factory() as uow:
            events = uow.audit_events.list_for_subject("blockchain_anchor", aid)
            return [
                {
                    "audit_event_id": str(e.audit_event_id),
                    "event_type": e.event_type,
                    "subject_kind": e.subject_kind,
                    "subject_id": str(e.subject_id),
                    "payload": e.payload,
                    "recorded_at": e.recorded_at.isoformat() if e.recorded_at else None,
                }
                for e in events
            ]
    except Exception as exc:
        logger.warning("list_audit_events_for_anchor falhou: %s", exc)
        return []
