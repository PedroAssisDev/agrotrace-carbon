"""Orquestrador local do ciclo completo EmissionCycle.

Usa o schema central de ``cycle_state`` e garante o encadeamento das etapas:
cada etapa lê os artefatos da anterior, atualiza o estado por etapa (status,
modo real/mock, resumo) e registra eventos de proveniência.
"""

from __future__ import annotations

import logging
from typing import Any

import config
from services import (
    blockchain_adapter,
    calculation_adapter,
    ontology_adapter,
    provenance_adapter,
    wrapper_adapter,
)
from services.cycle_state import (
    add_error,
    add_warning,
    new_cycle,
    set_milestone,
    set_pipeline_progress,
    set_step,
)
from services.mock_data import MOCK_FARM, mock_full_cycle
from services.pipeline_guards import (
    can_publish_final_ontology,
    can_run_calculation,
    can_run_ontology,
    can_run_semantic_validation,
    can_run_wrapper,
    can_unlock_blockchain,
)
from services.provenance_event_catalog import emit_pipeline_event
from utils.date_helpers import now_iso
from utils.file_helpers import save_cycle
from utils.pipeline_logging import (
    ids_from_cycle,
    log_decision,
    log_fail,
    log_pipe,
    timed_op,
    truncate,
)

logger = logging.getLogger("agrotrace.orchestrator")

# Cache em memória do objeto de ontologia (owlready2), que não é serializável em
# JSON e portanto não sobrevive ao roundtrip do dcc.Store entre callbacks.
from services import ontology_runtime_cache as _onto_cache


def _mode_of(result: dict | None) -> str:
    if not result:
        return "mock"
    return result.get("mode") or result.get("source") or "mock"


def _step_status(cycle: dict, step_id: str) -> str:
    return (cycle.get("steps") or {}).get(step_id, {}).get("status", "?")


def _log_step(
    cycle: dict,
    step_id: str,
    phase: str = "done",
    *,
    duration_ms: float | None = None,
    **extra: Any,
) -> None:
    fields = {
        **ids_from_cycle(cycle),
        "step": step_id,
        "status": _step_status(cycle, step_id),
        "milestone": cycle.get("current_status"),
        "duration_ms": duration_ms,
        **extra,
    }
    level = logging.WARNING if phase == "failed" else logging.INFO
    log_pipe(logger, f"step.{phase}", level=level, **fields)


def _log_gate_denied(cycle: dict, step_id: str, reason: str) -> None:
    log_decision(
        logger,
        "gate_denied",
        level=logging.WARNING,
        **ids_from_cycle(cycle),
        step=step_id,
        reason=reason,
    )


def _emit(cycle: dict, event_type: str, payload: dict) -> None:
    payload = dict(payload)
    payload.setdefault("cycle_id", cycle.get("cycle_id"))
    if cycle.get("pipeline_run_id"):
        payload.setdefault("pipeline_run_id", cycle["pipeline_run_id"])
    evt = provenance_adapter.register_provenance_event(event_type, payload)
    cycle.setdefault("provenance_events", []).append(evt)


def _emit_canonical(cycle: dict, event_type: str, payload: dict) -> None:
    emit_pipeline_event(cycle, event_type, payload, emit_fn=_emit)


def _layout_key_from_id(layout_id: str | None) -> str:
    if not layout_id:
        return "monthly"
    if ":" in layout_id:
        return layout_id.split(":", 1)[0]
    return layout_id


# ── Etapa 1: dados brutos ───────────────────────────────────────────────────
def register_raw_upload(cycle: dict, raw_meta: dict | None = None, **_: Any) -> dict[str, Any]:
    if raw_meta is None:
        raw_meta = cycle.get("raw_file")
    if not raw_meta:
        add_error(cycle, "raw_data", "Nenhum arquivo bruto informado.")
        set_step(cycle, "raw_data", status="ERROR")
        set_milestone(cycle, "FAILED")
        _log_step(cycle, "raw_data", "failed", error="Nenhum arquivo bruto informado.")
        return cycle

    set_pipeline_progress(cycle, "raw", "Salvando arquivo original")
    set_milestone(cycle, "RAW_DATA_RECEIVED")
    set_step(cycle, "raw_data", status="RUNNING")
    cycle["raw_file"] = raw_meta
    timer = timed_op()
    timer.__enter__()
    _log_step(
        cycle,
        "raw_data",
        "start",
        file=raw_meta.get("original_filename"),
    )

    year, month = _parse_period(cycle["reporting_period"])
    period_rec = provenance_adapter.record_reporting_period(year, month, cycle["reporting_period"])
    cycle["reporting_period_id"] = period_rec.get("reporting_period_id")

    run_rec = provenance_adapter.start_pipeline_run(
        cycle["property_id"], cycle["reporting_period"], f"run-{cycle['cycle_id']}"
    )
    cycle["pipeline_run_id"] = run_rec.get("pipeline_run_id")

    artifact_rec = provenance_adapter.record_source_artifact(cycle["pipeline_run_id"], raw_meta)
    cycle["source_artifact_id"] = artifact_rec.get("source_artifact_id")

    set_pipeline_progress(cycle, "hash", "Calculando hash SHA-256")
    set_milestone(cycle, "ORIGINAL_FILE_STORED")
    _emit_canonical(cycle, "RAW_DATA_UPLOADED", {"file": raw_meta.get("original_filename")})
    _emit_canonical(cycle, "RAW_FILE_HASH_CREATED", {
        "sha256": raw_meta.get("sha256"),
        "stored_path": raw_meta.get("stored_path"),
        "hash_algorithm": "SHA-256",
    })
    _emit(cycle, "RAW_DATA_REGISTERED", {"file": raw_meta.get("original_filename")})
    _emit(cycle, "ORIGINAL_FILE_STORED", {"stored_path": raw_meta.get("stored_path"), "sha256": raw_meta.get("sha256")})
    set_milestone(cycle, "RAW_DATA_REGISTERED")

    set_step(
        cycle,
        "raw_data",
        status="DONE",
        mode=_mode_of(run_rec),
        summary=f"Arquivo {raw_meta.get('original_filename')} registrado (SHA-256 {str(raw_meta.get('sha256',''))[:12]}…).",
    )
    save_cycle(cycle)
    timer.__exit__(None, None, None)
    _log_step(
        cycle,
        "raw_data",
        duration_ms=timer.duration_ms,
        mode=_mode_of(run_rec),
        sha256=truncate(raw_meta.get("sha256")),
        file=raw_meta.get("original_filename"),
    )
    return cycle


# ── Etapa 2 e 3: wrapper + normalização ─────────────────────────────────────
def run_wrapper_step(cycle: dict, layout_name: str = "monthly", **_: Any) -> dict[str, Any]:
    ok, msg = can_run_wrapper(cycle)
    if not ok:
        _log_gate_denied(cycle, "wrapper", msg)
        add_error(cycle, "wrapper", msg)
        set_step(cycle, "wrapper", status="ERROR")
        set_milestone(cycle, "FAILED")
        _log_step(cycle, "wrapper", "failed", error=msg)
        return cycle

    set_pipeline_progress(cycle, "wrapper", "Executando wrapper")
    set_step(cycle, "wrapper", status="RUNNING")
    _log_step(cycle, "wrapper", "start", layout=layout_name)
    _emit_canonical(cycle, "WRAPPER_EXECUTION_STARTED", {"layout": layout_name})

    with timed_op() as timer:
        raw_path = cycle["raw_file"]["stored_path"]
        wrapper_result = wrapper_adapter.run_wrapper(raw_path, layout_name, cycle["reporting_period"])
        cycle["wrapper"] = wrapper_result
        cycle["normalized_data"] = wrapper_result.get("normalized_payload", [])
        mode = _mode_of(wrapper_result)

        prov = provenance_adapter.record_wrapper_flow(
            cycle["pipeline_run_id"], cycle["raw_file"], wrapper_result,
            source_artifact_id=cycle.get("source_artifact_id"),
        )
        cycle["normalized_batch_id"] = prov.get("normalized_batch_id")
        cycle["wrapper_execution_id"] = prov.get("wrapper_execution_id")

        set_pipeline_progress(cycle, "normalized", "Gerando lote normalizado")
        _emit_canonical(cycle, "WRAPPER_EXECUTED", {"layout": wrapper_result.get("layout_id")})
        _emit(cycle, "NORMALIZED_BATCH_CREATED", {"rows": wrapper_result.get("rows_valid")})
        _emit_canonical(cycle, "NORMALIZED_DATA_DERIVED_FROM_RAW_DATA", {
            "source_hash": cycle["raw_file"].get("sha256"),
            "batch_hash": wrapper_result.get("content_hash"),
        })
        set_milestone(cycle, "WRAPPER_EXECUTED")
        set_milestone(cycle, "NORMALIZED_BATCH_CREATED")

        set_step(cycle, "wrapper", status="DONE", mode=mode,
                 summary=f"Layout {wrapper_result.get('layout_id')} • {wrapper_result.get('rows_valid')} linhas válidas.")
        set_step(cycle, "normalization", status="DONE", mode=mode,
                 summary=f"{wrapper_result.get('rows_valid')} registros normalizados, {wrapper_result.get('rows_rejected')} rejeitados.")
        save_cycle(cycle)

    _log_step(
        cycle,
        "wrapper",
        duration_ms=timer.duration_ms,
        mode=mode,
        layout=wrapper_result.get("layout_id"),
        rows_valid=wrapper_result.get("rows_valid"),
        rows_rejected=wrapper_result.get("rows_rejected"),
    )
    return cycle


# ── Etapa 4: modelo canônico ────────────────────────────────────────────────
def run_ontology_step(cycle: dict, **_: Any) -> dict[str, Any]:
    ok, msg = can_run_ontology(cycle)
    if not ok:
        _log_gate_denied(cycle, "ontology", msg)
        add_error(cycle, "ontology", msg)
        set_step(cycle, "ontology", status="ERROR")
        set_milestone(cycle, "FAILED")
        _log_step(cycle, "ontology", "failed", error=msg)
        return cycle

    set_pipeline_progress(cycle, "ontology", "Populando ontologia / modelo canônico")
    set_step(cycle, "ontology", status="RUNNING")
    _log_step(cycle, "ontology", "start")
    _emit_canonical(cycle, "CANONICAL_MODEL_POPULATION_STARTED", {})

    with timed_op() as timer:
        ontology_result = ontology_adapter.publish_to_canonical_model({
            **(cycle.get("wrapper") or {}),
            "normalized_payload": cycle.get("normalized_data") or (cycle.get("wrapper") or {}).get("normalized_payload") or [],
            "cycle_id": cycle.get("cycle_id"),
        })
        cycle["ontology"] = {k: v for k, v in ontology_result.items() if k != "_ontology"}
        if ontology_result.get("_ontology") is not None:
            _onto_cache.set_ontology(cycle["cycle_id"], ontology_result["_ontology"])
        mode = _mode_of(ontology_result)

        # Persiste Property/EmissionCycle + observações de atividade na OWL
        try:
            from services.ontology_result_service import persist_activity_observations

            persist_activity_observations(cycle)
        except Exception as exc:
            add_error(cycle, "ontology", f"Falha ao persistir observações na ontologia: {exc}")
            set_step(cycle, "ontology", status="ERROR", mode=mode)
            set_milestone(cycle, "FAILED")
            save_cycle(cycle)
            log_fail(
                logger,
                "step.failed",
                **ids_from_cycle(cycle),
                step="ontology",
                error=str(exc),
                duration_ms=timer.duration_ms,
            )
            return cycle

        if cycle.get("normalized_batch_id"):
            prov = provenance_adapter.record_semantic_and_canonical(
                cycle["pipeline_run_id"], cycle["normalized_batch_id"], ontology_result
            )
            cycle["canonical_snapshot_id"] = prov.get("canonical_snapshot_id")
            cycle["semantic_integration_id"] = prov.get("semantic_integration_id")

        _emit_canonical(cycle, "CANONICAL_MODEL_POPULATED", {"version": ontology_result.get("ontology_version")})
        _emit(cycle, "SEMANTIC_MAPPING_COMPLETED", {"entities": ontology_result.get("entities_created")})
        _emit(cycle, "CANONICAL_PUBLISHED", {"version": ontology_result.get("ontology_version")})
        set_milestone(cycle, "CANONICAL_MODEL_POPULATED")

        set_step(cycle, "ontology", status="DONE", mode=mode,
                 summary=f"{ontology_result.get('entities_created')} entidades • {ontology_result.get('relationships_created')} relações.")
        save_cycle(cycle)

    _log_step(
        cycle,
        "ontology",
        duration_ms=timer.duration_ms,
        mode=mode,
        entities=ontology_result.get("entities_created"),
        version=ontology_result.get("ontology_version"),
    )
    return cycle


# ── Etapa 5: validação semântica ────────────────────────────────────────────
def run_semantic_step(cycle: dict, **_: Any) -> dict[str, Any]:
    ok, msg = can_run_semantic_validation(cycle)
    if not ok:
        _log_gate_denied(cycle, "semantic", msg)
        add_error(cycle, "semantic", msg)
        set_step(cycle, "semantic", status="ERROR")
        set_milestone(cycle, "FAILED")
        _log_step(cycle, "semantic", "failed", error=msg)
        return cycle

    set_pipeline_progress(cycle, "semantic", "Validando semanticamente")
    set_step(cycle, "semantic", status="RUNNING")
    _log_step(cycle, "semantic", "start")
    _emit_canonical(cycle, "SEMANTIC_VALIDATION_STARTED", {})

    with timed_op() as timer:
        dataset = dict(cycle.get("ontology", {}))
        onto_obj = _onto_cache.get_ontology(cycle["cycle_id"])
        if onto_obj is not None:
            dataset["_ontology"] = onto_obj
        validation = ontology_adapter.run_semantic_validation(dataset)
        cycle["semantic_validation"] = validation
        mode = _mode_of(validation)
        critical = validation.get("critical_errors", 0)
        warns = validation.get("warnings", 0)

        _emit_canonical(cycle, "SEMANTIC_VALIDATION_COMPLETED", {"warnings": warns, "critical": critical})
        _emit(cycle, "SEMANTIC_VALIDATION_COMPLETED", {"warnings": warns, "critical": critical})

        if critical:
            add_error(cycle, "semantic", f"{critical} erro(s) crítico(s) de validação.")
            set_step(cycle, "semantic", status="ERROR", mode=mode,
                     summary=f"{critical} erro(s) crítico(s).")
            set_milestone(cycle, "FAILED")
        elif warns:
            add_warning(cycle, "semantic", f"{warns} alerta(s) de validação.")
            set_step(cycle, "semantic", status="DONE_WARNINGS", mode=mode,
                     summary=f"Aprovado com {warns} alerta(s).")
            set_milestone(cycle, "SEMANTIC_VALIDATION_COMPLETED")
        else:
            set_step(cycle, "semantic", status="DONE", mode=mode, summary="Validação aprovada sem alertas.")
            set_milestone(cycle, "SEMANTIC_VALIDATION_COMPLETED")
        save_cycle(cycle)

    phase = "failed" if critical else "done"
    _log_step(
        cycle,
        "semantic",
        phase,
        duration_ms=timer.duration_ms,
        mode=mode,
        critical=critical,
        warnings=warns,
    )
    return cycle


# ── Etapa 6: cálculo ────────────────────────────────────────────────────────
def run_calculation_step(cycle: dict, params: dict | None = None, **_: Any) -> dict[str, Any]:
    ok, msg = can_run_calculation(cycle)
    if not ok:
        _log_gate_denied(cycle, "calculation", msg)
        add_error(cycle, "calculation", msg)
        set_step(cycle, "calculation", status="ERROR")
        set_milestone(cycle, "FAILED")
        _log_step(cycle, "calculation", "failed", error=msg)
        return cycle

    set_pipeline_progress(cycle, "calculation", "Executando cálculo de emissões")
    set_step(cycle, "calculation", status="RUNNING")
    stored_params = cycle.get("calculation_params") or {}
    params = {**stored_params, **(params or {})}
    if "temporal_scope" not in params:
        freq = cycle.get("frequency") or cycle.get("granularity")
        if freq:
            params["temporal_scope"] = freq
    if "reporting_period" not in params and cycle.get("reporting_period"):
        params["reporting_period"] = cycle["reporting_period"]
    if "gwp" not in params:
        from services import direct_imports as di
        if di.gwp_ipcc_ar4 is None:
            add_error(cycle, "calculation", "GWP indisponível (emissions.defaults.gwp_ipcc_ar4).")
            set_step(cycle, "calculation", status="ERROR")
            set_milestone(cycle, "FAILED")
            _log_step(cycle, "calculation", "failed", error="GWP indisponível")
            return cycle
        params["gwp"] = di.gwp_ipcc_ar4()
    cycle["calculation_params"] = params

    # Materialização oficial do catálogo (defaults pending) antes do adapter
    try:
        from services.factor_catalog_materialization_service import (
            ensure_factor_catalog_for_calculation,
        )
        from services import provenance_adapter as _prov_cat

        factor_catalog = ensure_factor_catalog_for_calculation(cycle)
        if cycle.get("pipeline_run_id"):
            _prov_cat.record_factor_catalog_materialization(
                cycle["pipeline_run_id"], cycle, factor_catalog,
            )
    except Exception as exc:
        add_error(cycle, "calculation", str(exc))
        set_step(cycle, "calculation", status="ERROR")
        set_milestone(cycle, "FAILED")
        _log_step(cycle, "calculation", "failed", error=str(exc))
        save_cycle(cycle)
        return cycle

    _log_step(cycle, "calculation", "start")
    _emit_canonical(cycle, "CALCULATION_EXECUTION_STARTED", {"gwp": params.get("gwp")})

    calc_input = {
        **(cycle.get("ontology") or {}),
        "normalized_data": cycle.get("normalized_data") or [],
        "normalized_payload": cycle.get("normalized_data") or [],
        "reporting_period": cycle.get("reporting_period"),
        "frequency": cycle.get("frequency") or cycle.get("granularity"),
        "wrapper": cycle.get("wrapper") or {},
        "calculation_params": params,
        "factor_catalog": factor_catalog,
        "ontology": cycle.get("ontology") or {},
    }
    with timed_op() as timer:
        try:
            calculation = calculation_adapter.run_emission_calculation(calc_input, params)
        except Exception as exc:
            add_error(cycle, "calculation", str(exc))
            set_step(cycle, "calculation", status="ERROR")
            set_milestone(cycle, "FAILED")
            _emit(cycle, "PIPELINE_STEP_FAILED", {"step": "calculation", "error": str(exc)})
            save_cycle(cycle)
            _log_step(cycle, "calculation", "failed", duration_ms=timer.duration_ms, error=str(exc))
            return cycle

        # Persistência oficial na ontologia + releitura (fonte de verdade)
        result_status = "recalculated" if cycle.get("ontology_results") else "preliminary"
        try:
            from services.ontology_result_service import persist_calculation_results
            from services.ontology_query_adapter import get_emission_summary_for_cycle

            persist_calculation_results(cycle, calculation, status=result_status)
            summary = get_emission_summary_for_cycle(cycle)
            calculation["ontology_summary"] = summary
            calculation["domain_source"] = "ontology"
            # Espelho deprecated no JSON apenas para orquestração/compat — UI deve usar query
            calculation["_deprecated_mirror"] = True
        except Exception as exc:
            add_error(cycle, "calculation", f"Falha ao persistir/releitura de resultados na ontologia: {exc}")
            set_step(cycle, "calculation", status="ERROR")
            set_milestone(cycle, "FAILED")
            save_cycle(cycle)
            _log_step(cycle, "calculation", "failed", duration_ms=timer.duration_ms, error=str(exc))
            return cycle

        cycle["calculation"] = calculation
        mode = _mode_of(calculation)

        pending_corr = cycle.get("_pending_correction") or {}
        supersedes_id = pending_corr.get("supersedes_id") or None
        correction_reason = pending_corr.get("correction_reason")

        if cycle.get("canonical_snapshot_id") and cycle.get("reporting_period_id") and cycle.get("pipeline_run_id"):
            try:
                prov = provenance_adapter.record_calculation_flow(
                    cycle["pipeline_run_id"], cycle["canonical_snapshot_id"],
                    cycle["reporting_period_id"], calculation,
                    supersedes_id=supersedes_id,
                    correction_reason=correction_reason,
                )
                cycle["calculation_execution_id"] = prov.get("calculation_execution_id")
                cycle["calculation_result_set_id"] = prov.get("calculation_result_set_id")
                if prov.get("prov_entity_id"):
                    cycle["_last_result_prov_entity_id"] = prov.get("prov_entity_id")

                if supersedes_id and prov.get("calculation_result_set_id"):
                    try:
                        rev = provenance_adapter.record_result_revision(
                            supersedes_id,
                            prov["calculation_result_set_id"],
                            reason=correction_reason or "correction_recalculation",
                            invalidate_previous=False,
                        )
                        cycle.setdefault("provenance_mirrors", {})["result_revision"] = rev
                    except Exception as exc:
                        logger.warning("record_result_revision falhou: %s", exc)
            except Exception as exc:
                logger.warning("record_calculation_flow falhou (espelho soft): %s", exc)

            if pending_corr:
                try:
                    from services.result_correction_service import register_recalculated_version

                    cycle = register_recalculated_version(cycle, pending_corr)
                    cycle.pop("_pending_correction", None)
                except Exception as exc:
                    logger.warning("register_recalculated_version falhou: %s", exc)
            elif not cycle.get("result_versions"):
                try:
                    from services.result_correction_service import _ensure_v1

                    cycle = _ensure_v1(cycle)
                except Exception as exc:
                    logger.warning("ensure_v1 falhou: %s", exc)

        _emit_canonical(cycle, "CALCULATION_EXECUTED", {"co2e_total_kg": calculation.get("co2e_total_kg")})
        _emit_canonical(cycle, "PRELIMINARY_RESULT_CREATED", {
            "co2e_total_kg": calculation.get("co2e_total_kg"),
            "preliminary_hash": calculation.get("preliminary_hash"),
        })
        _emit(cycle, "CALCULATION_PRELIMINARY_RESULT_CREATED", {"co2e_total_kg": calculation.get("co2e_total_kg")})
        set_milestone(cycle, "CALCULATION_EXECUTED")

        co2e = calculation.get("co2e_total_kg", 0)
        set_step(cycle, "calculation", status="DONE", mode=mode,
                 summary=f"{co2e:,.1f} kg CO₂e • intensidade {calculation.get('co2e_intensity_per_milk_liter', 0):.3f} kg CO₂e/L.")
        save_cycle(cycle)

    _log_step(
        cycle,
        "calculation",
        duration_ms=timer.duration_ms,
        mode=mode,
        co2e_total_kg=calculation.get("co2e_total_kg"),
    )
    return cycle


# ── Etapa 7: aprovação humana ───────────────────────────────────────────────
def run_approval_step(cycle: dict, approval: dict | None = None, **_: Any) -> dict[str, Any]:
    if not cycle.get("calculation"):
        add_error(cycle, "approval", "Execute o cálculo primeiro.")
        set_step(cycle, "approval", status="ERROR")
        _log_step(cycle, "approval", "failed", error="Execute o cálculo primeiro.")
        return cycle

    approval = approval or {"decision": "APPROVED", "approver": "Dr. Ana Souza",
                            "justification": "Aprovado via pipeline."}
    approval["approved_at"] = now_iso()
    cycle["approval"] = approval
    decision = approval.get("decision", "APPROVED")
    _log_step(cycle, "approval", "start", decision=decision, approver=approval.get("approver"))

    with timed_op() as timer:
        prov = {}
        if cycle.get("calculation_result_set_id") and cycle.get("reporting_period_id"):
            prov = provenance_adapter.record_approval(
                cycle["pipeline_run_id"], cycle["calculation_result_set_id"],
                cycle["reporting_period_id"], approval,
            )

        if decision == "APPROVED":
            _emit_canonical(cycle, "CALCULATION_APPROVED", {"decision": decision})
            _emit(cycle, "CALCULATION_APPROVED", {"decision": decision})
            set_step(cycle, "approval", status="APPROVED", mode=_mode_of(prov),
                     summary=f"Aprovado por {approval.get('approver')}.")
            set_milestone(cycle, "CALCULATION_APPROVED")
        elif decision == "REJECTED":
            _emit(cycle, "CALCULATION_REJECTED", {"decision": decision})
            set_step(cycle, "approval", status="ERROR", mode=_mode_of(prov),
                     summary=f"Reprovado por {approval.get('approver')}.")
            set_milestone(cycle, "REJECTED")
        else:
            _emit(cycle, "CALCULATION_CORRECTION_REQUESTED", {"decision": decision})
            set_step(cycle, "approval", status="DONE_WARNINGS", mode=_mode_of(prov),
                     summary=f"Decisão: {decision}.")
            set_milestone(cycle, "CORRECTION_REQUESTED")

        save_cycle(cycle)

    log_decision(
        logger,
        "approval",
        **ids_from_cycle(cycle),
        decision=decision,
        approver=approval.get("approver"),
        status=_step_status(cycle, "approval"),
        duration_ms=timer.duration_ms,
    )
    _log_step(
        cycle,
        "approval",
        duration_ms=timer.duration_ms,
        decision=decision,
        mode=_mode_of(prov) if prov else None,
    )
    return cycle


# ── Etapa 8: publicação final ───────────────────────────────────────────────
def run_publication_step(cycle: dict, **_: Any) -> dict[str, Any]:
    ok, msg = can_publish_final_ontology(cycle)
    if not ok:
        _log_gate_denied(cycle, "publication", msg)
        add_error(cycle, "publication", msg)
        set_step(cycle, "publication", status="ERROR")
        _log_step(cycle, "publication", "failed", error=msg)
        return cycle

    set_step(cycle, "publication", status="RUNNING")
    _log_step(cycle, "publication", "start")

    with timed_op() as timer:
        try:
            from services.publication_service import publish_approved_cycle

            publication = publish_approved_cycle(cycle)
        except Exception as exc:
            add_error(cycle, "publication", str(exc))
            set_step(cycle, "publication", status="ERROR")
            _emit(cycle, "PIPELINE_STEP_FAILED", {"step": "publication", "error": str(exc)})
            save_cycle(cycle)
            _log_step(cycle, "publication", "failed", duration_ms=timer.duration_ms, error=str(exc))
            return cycle

        cycle["publication"] = publication
        prov = {}
        if cycle.get("calculation_result_set_id"):
            prov = provenance_adapter.record_publication(
                cycle["pipeline_run_id"], cycle["calculation_result_set_id"], publication
            )

        _emit(cycle, "APPROVED_RESULT_PUBLISHED", {
            "publication_id": publication.get("publication_id"),
            "publication_hash": publication.get("publication_hash"),
            "version": publication.get("ontology_version"),
        })
        # Compatibilidade de leitura com ciclos/UI que ainda checam o marco legado
        set_milestone(cycle, "APPROVED_RESULT_PUBLISHED")
        set_milestone(cycle, "FINAL_ONTOLOGY_PUBLISHED")
        set_milestone(cycle, "BLOCKCHAIN_UNLOCKED")

        set_step(
            cycle,
            "publication",
            status="DONE",
            mode=_mode_of(prov) if prov else "real",
            summary=(
                f"Publicação {str(publication.get('publication_id', ''))[:12]}… "
                f"hash {str(publication.get('publication_hash', ''))[:12]}…"
            ),
        )
        save_cycle(cycle)

    _log_step(
        cycle,
        "publication",
        duration_ms=timer.duration_ms,
        mode=_mode_of(prov) if prov else "real",
        publication_id=truncate(publication.get("publication_id")),
        publication_hash=truncate(publication.get("publication_hash")),
        version=publication.get("ontology_version"),
    )
    return cycle


# ── Etapa 9: pacote de evidências ───────────────────────────────────────────
def run_evidence_step(cycle: dict, **_: Any) -> dict[str, Any]:
    ok, msg = can_unlock_blockchain(cycle)
    if not ok:
        _log_gate_denied(cycle, "evidence", msg)
        add_error(cycle, "evidence", f"Blockchain bloqueado: {msg}")
        set_step(cycle, "evidence", status="ERROR")
        _log_step(cycle, "evidence", "failed", error=msg)
        return cycle

    set_step(cycle, "evidence", status="RUNNING")
    _log_step(cycle, "evidence", "start")

    with timed_op() as timer:
        cycle["hashes"] = blockchain_adapter.compute_local_hashes(cycle)
        _emit_canonical(cycle, "ARTIFACT_HASHES_CREATED", {"hashes": list(cycle["hashes"].keys())})

        try:
            evidence = blockchain_adapter.create_evidence_package(cycle)
        except Exception as exc:
            add_error(cycle, "evidence", f"Falha ao construir pacote: {exc}")
            set_step(cycle, "evidence", status="ERROR")
            save_cycle(cycle)
            _log_step(cycle, "evidence", "failed", duration_ms=timer.duration_ms, error=str(exc))
            return cycle

        cycle["evidence_package"] = evidence
        mode = _mode_of(evidence)
        _emit_canonical(cycle, "EVIDENCE_PACKAGE_CREATED", {"package_id": evidence.get("evidence_package_id")})
        _emit(cycle, "EVIDENCE_PACKAGE_CREATED", {"package_id": evidence.get("evidence_package_id")})
        _emit_canonical(cycle, "MERKLE_ROOT_CREATED", {"merkle_root": evidence.get("merkle_root")})
        _emit(cycle, "LOCAL_HASH_CREATED", {"merkle_root": evidence.get("merkle_root")})
        set_milestone(cycle, "EVIDENCE_PACKAGE_CREATED")
        set_milestone(cycle, "MERKLE_ROOT_CREATED")

        set_step(cycle, "evidence", status="DONE", mode=mode,
                 summary=f"Pacote {str(evidence.get('evidence_package_id'))[:12]}… • Merkle {str(evidence.get('merkle_root',''))[:12]}…")
        save_cycle(cycle)

    _log_step(
        cycle,
        "evidence",
        duration_ms=timer.duration_ms,
        mode=mode,
        package_id=truncate(evidence.get("evidence_package_id")),
        merkle_root=truncate(evidence.get("merkle_root")),
        hash_count=len(cycle.get("hashes") or {}),
    )
    return cycle


# ── Etapa 10: blockchain (ancoragem) ────────────────────────────────────────
def run_anchoring_step(cycle: dict, **_: Any) -> dict[str, Any]:
    ok, msg = can_unlock_blockchain(cycle)
    if not ok:
        _log_gate_denied(cycle, "blockchain", msg)
        add_error(cycle, "blockchain", f"Blockchain bloqueado: {msg}")
        set_step(cycle, "blockchain", status="ERROR")
        _log_step(cycle, "blockchain", "failed", error=msg)
        return cycle
    if not cycle.get("evidence_package"):
        add_error(cycle, "blockchain", "Construa o pacote de evidências primeiro.")
        set_step(cycle, "blockchain", status="ERROR")
        _log_step(cycle, "blockchain", "failed", error="Pacote de evidências ausente")
        return cycle

    set_step(cycle, "blockchain", status="RUNNING")
    pkg_id = cycle["evidence_package"].get("evidence_package_id", "")
    _log_step(cycle, "blockchain", "start", package_id=truncate(pkg_id))
    _emit_canonical(cycle, "ANCHOR_REQUEST_CREATED", {"package_id": pkg_id})

    try:
        from services import provenance_adapter as _prov

        import config as app_config

        network = getattr(app_config, "BLOCKCHAIN_DEFAULT_NETWORK_CODE", "local_simulated")
        req_mirror = _prov.record_anchor_request(
            cycle,
            cycle.get("evidence_package") or {},
            {
                "network_code": network,
                "request_id": (cycle.get("evidence_package") or {}).get("anchor_request_id") or pkg_id,
                "agent": "frontend.local_orchestrator",
            },
        )
        cycle.setdefault("provenance_mirrors", {})["anchor_request"] = req_mirror
    except Exception as exc:
        logger.warning("Espelho de solicitação de ancoragem falhou: %s", exc)

    with timed_op() as timer:
        try:
            import config as app_config

            network = getattr(app_config, "BLOCKCHAIN_DEFAULT_NETWORK_CODE", "local_simulated")
            anchor = blockchain_adapter.simulate_anchoring(pkg_id, network_code=network)
        except Exception as exc:
            add_error(cycle, "blockchain", f"Falha na ancoragem: {exc}")
            set_step(cycle, "blockchain", status="ERROR")
            save_cycle(cycle)
            _log_step(cycle, "blockchain", "failed", duration_ms=timer.duration_ms, error=str(exc))
            return cycle

        cycle["anchoring"] = anchor
        cycle["evidence_package"]["anchoring_status"] = anchor.get("anchoring_status", "ANCHORING_SIMULATED")
        cycle["evidence_package"]["transaction_id"] = anchor.get("transaction_id")
        cycle["evidence_package"]["block_number"] = anchor.get("block_number")
        cycle["evidence_package"]["network"] = anchor.get("network")
        cycle["evidence_package"]["package_hash"] = (
            cycle["evidence_package"].get("package_hash") or anchor.get("package_hash")
        )
        cycle["evidence_package"]["merkle_root"] = (
            cycle["evidence_package"].get("merkle_root") or anchor.get("merkle_root")
        )
        mode = _mode_of(anchor)
        kind = anchor.get("anchoring_kind", "SIMULADA")
        is_simulated = kind == "SIMULADA" or anchor.get("network") == "local_simulated"

        try:
            from services import provenance_adapter as _prov

            conf_mirror = _prov.record_anchor_confirmation(cycle, anchor)
            cycle.setdefault("provenance_mirrors", {})["anchor_confirmation"] = conf_mirror
        except Exception as exc:
            logger.warning("Espelho de confirmação de ancoragem falhou: %s", exc)

        event_name = "ANCHORING_SIMULATED" if is_simulated else "BLOCKCHAIN_ANCHOR_CREATED"
        _emit_canonical(cycle, event_name, {"tx": anchor.get("transaction_id"), "network": anchor.get("network")})
        _emit(cycle, event_name, {"tx": anchor.get("transaction_id")})
        set_milestone(cycle, event_name)

        summary_label = "simulado" if is_simulated else f"EVM {anchor.get('network')}"
        set_step(cycle, "blockchain", status="ANCHORED", mode=mode,
                 summary=f"Ancorado ({summary_label}) • tx {str(anchor.get('transaction_id',''))[:14]}…")
        save_cycle(cycle)

    _log_step(
        cycle,
        "blockchain",
        duration_ms=timer.duration_ms,
        mode=mode,
        network=anchor.get("network"),
        tx=truncate(anchor.get("transaction_id"), 14),
        simulated=is_simulated,
    )
    return cycle


# ── Etapa 11: verificação ───────────────────────────────────────────────────
def run_verification_step(cycle: dict, tamper: bool = False, **_: Any) -> dict[str, Any]:
    ok, msg = can_unlock_blockchain(cycle)
    if not ok:
        _log_gate_denied(cycle, "verification", msg)
        add_error(cycle, "verification", f"Blockchain bloqueado: {msg}")
        set_step(cycle, "verification", status="ERROR")
        _log_step(cycle, "verification", "failed", error=msg)
        return cycle
    if not cycle.get("evidence_package"):
        add_error(cycle, "verification", "Construa e ancore o pacote primeiro.")
        set_step(cycle, "verification", status="ERROR")
        _log_step(cycle, "verification", "failed", error="Pacote de evidências ausente")
        return cycle

    set_step(cycle, "verification", status="RUNNING")
    _log_step(cycle, "verification", "start", tamper=tamper)

    with timed_op() as timer:
        integrity = blockchain_adapter.verify_integrity(cycle.get("evidence_package", {}), {"tamper": tamper})
        cycle["integrity"] = integrity
        mode = _mode_of(integrity)

        try:
            from services import provenance_adapter as _prov

            ver_mirror = _prov.record_integrity_verification(cycle, integrity)
            cycle.setdefault("provenance_mirrors", {})["integrity_verification"] = ver_mirror
        except Exception as exc:
            logger.warning("Espelho de verificação de integridade falhou: %s", exc)

        _emit_canonical(cycle, "INTEGRITY_VERIFICATION_EXECUTED", {"is_valid": integrity.get("is_valid")})
        _emit(cycle, "VERIFICATION_EXECUTED", {"is_valid": integrity.get("is_valid")})
        set_milestone(cycle, "INTEGRITY_VERIFICATION_EXECUTED")

        if integrity.get("is_valid"):
            _emit_canonical(cycle, "PROVENANCE_CHAIN_VERIFIED", {"cycle_id": cycle.get("cycle_id")})
            set_milestone(cycle, "PROVENANCE_CHAIN_VERIFIED")
            set_milestone(cycle, "VERIFIED")
            set_step(cycle, "verification", status="VERIFIED", mode=mode, summary="Pacote íntegro.")
        else:
            set_step(cycle, "verification", status="DIVERGENT", mode=mode, summary="Divergência detectada.")
        save_cycle(cycle)

    _log_step(
        cycle,
        "verification",
        duration_ms=timer.duration_ms,
        mode=mode,
        is_valid=integrity.get("is_valid"),
        status=_step_status(cycle, "verification"),
    )
    return cycle


# ── Pipeline automática pós-ingestão ────────────────────────────────────────
def run_auto_pipeline_after_ingestion(
    raw_meta: dict,
    *,
    property_id: str,
    property_name: str,
    reporting_period: str,
    layout_name: str = "monthly",
    layout_id: str | None = None,
    frequency: str | None = None,
    uploaded_by: str | None = None,
    calculation_params: dict | None = None,
    cycle_id: str | None = None,
    mark_pending: bool = True,
) -> dict[str, Any]:
    """Executa automaticamente ingestão → cálculo preliminar → pendência de aprovação."""
    from services.cycle_status_service import mark_pending_approval

    with timed_op() as timer:
        log_pipe(
            logger,
            "auto_pipeline.start",
            property_id=property_id,
            period=reporting_period,
            layout=layout_name,
            frequency=frequency,
            cycle_id=cycle_id,
        )

        cycle = new_cycle(
            property_id,
            property_name,
            reporting_period,
            frequency=frequency,
            layout_id=layout_id,
            uploaded_by=uploaded_by,
            calculation_params=calculation_params,
        )
        if cycle_id:
            cycle["cycle_id"] = cycle_id
        cycle["raw_file"] = raw_meta

        cycle = register_raw_upload(cycle, raw_meta)
        if cycle.get("steps", {}).get("raw_data", {}).get("status") == "ERROR":
            log_fail(
                logger,
                "auto_pipeline.failed",
                **ids_from_cycle(cycle),
                step="raw_data",
                duration_ms=timer.duration_ms,
            )
            return cycle

        cycle = run_wrapper_step(cycle, layout_name)
        if cycle.get("steps", {}).get("wrapper", {}).get("status") == "ERROR":
            log_fail(
                logger,
                "auto_pipeline.failed",
                **ids_from_cycle(cycle),
                step="wrapper",
                duration_ms=timer.duration_ms,
            )
            return cycle

        cycle = run_ontology_step(cycle)
        if cycle.get("steps", {}).get("ontology", {}).get("status") == "ERROR":
            log_fail(
                logger,
                "auto_pipeline.failed",
                **ids_from_cycle(cycle),
                step="ontology",
                duration_ms=timer.duration_ms,
            )
            return cycle

        cycle = run_semantic_step(cycle)
        if cycle.get("steps", {}).get("semantic", {}).get("status") == "ERROR":
            log_fail(
                logger,
                "auto_pipeline.failed",
                **ids_from_cycle(cycle),
                step="semantic",
                duration_ms=timer.duration_ms,
            )
            return cycle

        cycle = run_calculation_step(cycle, calculation_params)
        if cycle.get("steps", {}).get("calculation", {}).get("status") == "ERROR":
            log_fail(
                logger,
                "auto_pipeline.failed",
                **ids_from_cycle(cycle),
                step="calculation",
                duration_ms=timer.duration_ms,
            )
            return cycle

        if mark_pending:
            cycle = mark_pending_approval(cycle)
            set_pipeline_progress(cycle, "pending", "Aguardando aprovação humana")
        save_cycle(cycle)
        log_pipe(
            logger,
            "auto_pipeline.done",
            **ids_from_cycle(cycle),
            status=cycle.get("current_status"),
            errors=len(cycle.get("errors") or []),
            duration_ms=timer.duration_ms,
        )
    return cycle


def run_auto_pipeline_after_approval(cycle: dict, approval: dict) -> dict[str, Any]:
    """Continua automaticamente após decisão humana.

    Exige revisão por item aprovada (ou aprova itens obrigatórios quando o caller
    já passou ``approval.decision=APPROVED`` e os itens ainda estão pendentes
    apenas em scripts legados — preferir ``finalize_file_approval``).
    """
    decision = approval.get("decision", "APPROVED")

    with timed_op() as timer:
        log_pipe(
            logger,
            "post_approval.start",
            **ids_from_cycle(cycle),
            decision=decision,
            approver=approval.get("approver"),
        )

        if decision == "APPROVED":
            from services.calculation_approval_service import APPROVED_STATUSES, can_finalize
            from services.calculation_review_service import build_calculation_review

            if not cycle.get("calculation_review"):
                cycle["calculation_review"] = build_calculation_review(cycle)
            ok, msg = can_finalize(cycle)
            if not ok:
                # Auto-aprova itens pendentes somente se o caller já decidiu APPROVED
                # no nível do arquivo (caminho de script/smoke); UI deve usar finalize_file_approval.
                from services.calculation_approval_service import approve_item

                review = cycle["calculation_review"]
                pending_ids = []
                for it in review.get("items") or []:
                    st = it.get("status", "AWAITING_REVIEW")
                    if st in APPROVED_STATUSES or st in {"NOT_APPLICABLE", "REJECTED"}:
                        continue
                    if st == "REJECTED":
                        add_error(cycle, "publication", msg)
                        set_step(cycle, "publication", status="ERROR")
                        save_cycle(cycle)
                        log_fail(
                            logger,
                            "post_approval.failed",
                            **ids_from_cycle(cycle),
                            step="publication",
                            error=msg,
                            duration_ms=timer.duration_ms,
                        )
                        return cycle
                    pending_ids.append(it["calculation_item_id"])
                if pending_ids:
                    log_decision(
                        logger,
                        "auto_approve_items",
                        **ids_from_cycle(cycle),
                        count=len(pending_ids),
                    )
                for item_id in pending_ids:
                    cycle = approve_item(
                        cycle,
                        item_id,
                        reviewer=approval.get("approver") or "Sistema",
                        justification=approval.get("justification") or "Aprovado no fluxo pós-decisão.",
                    )
                review = cycle["calculation_review"]
                review["status"] = "APPROVED"
                cycle["calculation_review"] = review
                ok, msg = can_finalize(cycle)
                if not ok:
                    add_error(cycle, "publication", msg)
                    set_step(cycle, "publication", status="ERROR")
                    save_cycle(cycle)
                    log_fail(
                        logger,
                        "post_approval.failed",
                        **ids_from_cycle(cycle),
                        step="publication",
                        error=msg,
                        duration_ms=timer.duration_ms,
                    )
                    return cycle

        cycle = run_approval_step(cycle, approval)

        if decision != "APPROVED":
            cycle.pop("publication", None)
            cycle.pop("evidence_package", None)
            cycle.pop("anchoring", None)
            cycle.pop("integrity", None)
            cycle["hashes"] = {}
            save_cycle(cycle)
            log_pipe(
                logger,
                "post_approval.stopped",
                **ids_from_cycle(cycle),
                decision=decision,
                duration_ms=timer.duration_ms,
            )
            return cycle

        cycle = run_publication_step(cycle)
        if cycle.get("steps", {}).get("publication", {}).get("status") == "ERROR":
            log_fail(
                logger,
                "post_approval.failed",
                **ids_from_cycle(cycle),
                step="publication",
                duration_ms=timer.duration_ms,
            )
            return cycle

        cycle = run_evidence_step(cycle)
        if cycle.get("steps", {}).get("evidence", {}).get("status") == "ERROR":
            log_fail(
                logger,
                "post_approval.failed",
                **ids_from_cycle(cycle),
                step="evidence",
                duration_ms=timer.duration_ms,
            )
            return cycle

        cycle = run_anchoring_step(cycle)
        if cycle.get("steps", {}).get("blockchain", {}).get("status") == "ERROR":
            log_fail(
                logger,
                "post_approval.failed",
                **ids_from_cycle(cycle),
                step="blockchain",
                duration_ms=timer.duration_ms,
            )
            return cycle

        cycle = run_verification_step(cycle)
        log_pipe(
            logger,
            "post_approval.done",
            **ids_from_cycle(cycle),
            status=cycle.get("current_status"),
            verification=_step_status(cycle, "verification"),
            errors=len(cycle.get("errors") or []),
            duration_ms=timer.duration_ms,
        )
    return cycle

# ── Pipeline multi-entrada ──────────────────────────────────────────────────
def run_pipeline_group_until_pending(
    entries: list[dict[str, Any]],
    *,
    cycle_id: str,
    property_id: str,
    property_name: str,
    reporting_period: str,
    layout_name: str,
    data_granularity: str,
    approval_granularity: str,
    scenario_key: str | None = None,
    coverage_label: str | None = None,
    params: dict | None = None,
    frequency: str | None = None,
    layout_id: str | None = None,
    uploaded_by: str | None = None,
) -> dict[str, Any]:
    """Executa pipeline multi-entrada e para aguardando aprovação humana."""
    from pathlib import Path

    from services.cycle_status_service import mark_pending_approval
    from utils.file_helpers import save_raw_file

    if not entries:
        raise ValueError("Pelo menos uma entrada de dados é necessária.")

    data_entries: list[dict[str, Any]] = []
    wrapper_runs: list[dict[str, Any]] = []

    for entry in entries:
        src = Path(entry["path"])
        raw_meta = save_raw_file(
            src,
            property_id=entry.get("property_id") or property_id,
            reporting_period=entry["reporting_period"],
            original_filename=entry.get("original_filename") or src.name,
        )
        data_entries.append({
            "entry_id": entry["entry_id"],
            "reporting_period": entry["reporting_period"],
            "stored_path": raw_meta.get("stored_path"),
            "sha256": raw_meta.get("sha256"),
        })

    first_raw = {
        "original_filename": entries[0].get("original_filename") or Path(entries[0]["path"]).name,
        "stored_path": data_entries[0]["stored_path"],
        "property_id": property_id,
        "reporting_period": entries[0]["reporting_period"],
        "sha256": data_entries[0].get("sha256"),
    }

    cycle = run_auto_pipeline_after_ingestion(
        first_raw,
        cycle_id=cycle_id,
        property_id=property_id,
        property_name=property_name,
        reporting_period=reporting_period,
        layout_name=layout_name,
        layout_id=layout_id,
        frequency=frequency or data_granularity,
        uploaded_by=uploaded_by,
        calculation_params=params,
        mark_pending=False,
    )
    cycle["granularity"] = approval_granularity
    cycle["data_entries"] = data_entries

    merged = list(cycle.get("normalized_data") or [])
    wrapper_runs.append({
        "entry_id": entries[0]["entry_id"],
        "reporting_period": entries[0]["reporting_period"],
        "path": data_entries[0]["stored_path"],
        "rows": len(merged),
    })

    for entry, stored in zip(entries[1:], data_entries[1:]):
        extra = wrapper_adapter.run_wrapper(
            stored["stored_path"],
            layout_name,
            entry["reporting_period"],
        )
        rows = extra.get("normalized_payload") or []
        merged.extend(rows)
        wrapper_runs.append({
            "entry_id": entry["entry_id"],
            "reporting_period": entry["reporting_period"],
            "path": stored["stored_path"],
            "rows": len(rows),
        })

    cycle["normalized_data"] = merged
    cycle["wrapper_runs"] = wrapper_runs
    if cycle.get("wrapper"):
        cycle["wrapper"]["rows_valid"] = len(merged)
        if len(entries) > 1:
            cycle["wrapper"]["summary_note"] = f"{len(entries)} entradas agregadas"

    cycle["temporal_coverage"] = {
        "kind": scenario_key or "seed_group",
        "source_granularity": data_granularity,
        "granularity": approval_granularity,
        "data_entry_count": len(entries),
        "entry_ids": [e["entry_id"] for e in entries],
        "label": coverage_label or reporting_period,
    }
    if coverage_label:
        cycle["period_label"] = coverage_label

    if cycle.get("steps", {}).get("calculation", {}).get("status") != "DONE":
        cycle = run_ontology_step(cycle)
        cycle = run_semantic_step(cycle)
        cycle = run_calculation_step(cycle, params)

    cycle = mark_pending_approval(cycle)
    set_pipeline_progress(cycle, "pending", "Aguardando aprovação humana")
    save_cycle(cycle)
    return cycle


def run_pipeline_until_pending_approval(
    raw_meta: dict,
    *,
    cycle_id: str | None = None,
    property_id: str,
    property_name: str,
    reporting_period: str,
    layout_name: str = "monthly",
    granularity: str | None = None,
    params: dict | None = None,
    layout_id: str | None = None,
    uploaded_by: str | None = None,
) -> dict[str, Any]:
    """Compatibilidade: delega para run_auto_pipeline_after_ingestion."""
    cycle = run_auto_pipeline_after_ingestion(
        raw_meta,
        cycle_id=cycle_id,
        property_id=property_id,
        property_name=property_name,
        reporting_period=reporting_period,
        layout_name=layout_name,
        layout_id=layout_id,
        frequency=granularity,
        uploaded_by=uploaded_by,
        calculation_params=params,
    )
    if granularity:
        cycle["granularity"] = granularity
        save_cycle(cycle)
    return cycle


# ── Pipeline completo (demo/scripts) ────────────────────────────────────────
def run_full_pipeline(
    raw_meta: dict,
    *,
    property_id: str = MOCK_FARM["property_id"],
    property_name: str = MOCK_FARM["name"],
    reporting_period: str = "2026-01",
    layout_name: str = "monthly",
    approval: dict | None = None,
    params: dict | None = None,
) -> dict[str, Any]:
    """Pipeline completo com aprovação simulada — apenas demo/scripts."""
    cycle = run_auto_pipeline_after_ingestion(
        raw_meta,
        property_id=property_id,
        property_name=property_name,
        reporting_period=reporting_period,
        layout_name=layout_name,
        calculation_params=params,
    )
    cycle["demo_mode"] = True
    approval_payload = approval or {
        "decision": "APPROVED",
        "approver": "Dr. Ana Souza",
        "justification": "Aprovado via pipeline automático (modo demonstração).",
    }
    return run_auto_pipeline_after_approval(cycle, approval_payload)


# Mapa step_id → função do orquestrador (usado pelo wizard)
STEP_RUNNERS = {
    "raw_data": register_raw_upload,
    "wrapper": run_wrapper_step,
    "normalization": run_wrapper_step,
    "ontology": run_ontology_step,
    "semantic": run_semantic_step,
    "calculation": run_calculation_step,
    "approval": run_approval_step,
    "publication": run_publication_step,
    "evidence": run_evidence_step,
    "blockchain": run_anchoring_step,
    "verification": run_verification_step,
}


def run_step(cycle: dict, step_id: str, **kwargs: Any) -> dict[str, Any]:
    """Executa uma etapa pelo seu id (usado pelo wizard)."""
    runner = STEP_RUNNERS.get(step_id)
    if runner is None:
        add_error(cycle, step_id, f"Etapa desconhecida: {step_id}")
        return cycle
    return runner(cycle, **kwargs)


def load_or_seed_demo() -> dict[str, Any]:
    """Carrega ciclo ativo persistido ou estrutura vazia (sem auto-aprovar)."""
    from utils.file_helpers import get_active_cycle, list_cycles

    active = get_active_cycle()
    if active:
        return active
    cycles = list_cycles()
    if cycles:
        return cycles[0]
    if config.USE_MOCK_DATA:
        from services.mock_data import mock_pending_cycle

        demo = mock_pending_cycle()
        save_cycle(demo)
        return demo
    return new_cycle(MOCK_FARM["property_id"], MOCK_FARM["name"], "2026-01")


def _parse_period(period: str) -> tuple[int, int]:
    """Extrai (ano, mês) de períodos YYYY-MM, YYYY, YYYY-YYYY ou intervalo ISO."""
    import re

    period = (period or "").strip()
    if re.fullmatch(r"\d{4}", period):
        return int(period), 1
    if re.fullmatch(r"\d{4}-\d{4}", period):
        return int(period.split("-", 1)[0]), 1
    if "/" in period:
        start = period.split("/", 1)[0]
        y, m, *_ = start.split("-")
        return int(y), int(m)
    parts = period.split("-")
    year = int(parts[0])
    month = int(parts[1]) if len(parts) > 1 else 1
    return year, month


def resolve_layout_name(layout_id: str | None, default: str = "monthly") -> str:
    return _layout_key_from_id(layout_id or default)
