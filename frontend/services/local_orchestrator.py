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

logger = logging.getLogger("agrotrace.orchestrator")

# Cache em memória do objeto de ontologia (owlready2), que não é serializável em
# JSON e portanto não sobrevive ao roundtrip do dcc.Store entre callbacks.
_ONTOLOGY_CACHE: dict[str, Any] = {}


def _mode_of(result: dict | None) -> str:
    if not result:
        return "mock"
    return result.get("mode") or result.get("source") or "mock"


def _emit(cycle: dict, event_type: str, payload: dict) -> None:
    payload = dict(payload)
    payload.setdefault("cycle_id", cycle.get("cycle_id"))
    if cycle.get("pipeline_run_id"):
        payload.setdefault("pipeline_run_id", cycle["pipeline_run_id"])
    evt = provenance_adapter.register_provenance_event(event_type, payload)
    cycle.setdefault("provenance_events", []).append(evt)


def _emit_canonical(cycle: dict, event_type: str, payload: dict, *, include_legacy: bool = True) -> None:
    emit_pipeline_event(cycle, event_type, payload, emit_fn=_emit, include_legacy=include_legacy)


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
        return cycle

    set_pipeline_progress(cycle, "raw", "Salvando arquivo original")
    set_milestone(cycle, "RAW_DATA_RECEIVED")
    set_step(cycle, "raw_data", status="RUNNING")
    cycle["raw_file"] = raw_meta

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
    return cycle


# ── Etapa 2 e 3: wrapper + normalização ─────────────────────────────────────
def run_wrapper_step(cycle: dict, layout_name: str = "monthly", **_: Any) -> dict[str, Any]:
    ok, msg = can_run_wrapper(cycle)
    if not ok:
        add_error(cycle, "wrapper", msg)
        set_step(cycle, "wrapper", status="ERROR")
        set_milestone(cycle, "FAILED")
        return cycle

    set_pipeline_progress(cycle, "wrapper", "Executando wrapper")
    set_step(cycle, "wrapper", status="RUNNING")
    _emit_canonical(cycle, "WRAPPER_EXECUTION_STARTED", {"layout": layout_name}, include_legacy=False)

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
    _emit_canonical(cycle, "WRAPPER_EXECUTED", {"layout": wrapper_result.get("layout_id")}, include_legacy=False)
    _emit(cycle, "NORMALIZED_BATCH_CREATED", {"rows": wrapper_result.get("rows_valid")})
    _emit_canonical(cycle, "NORMALIZED_DATA_DERIVED_FROM_RAW_DATA", {
        "source_hash": cycle["raw_file"].get("sha256"),
        "batch_hash": wrapper_result.get("content_hash"),
    }, include_legacy=False)
    set_milestone(cycle, "WRAPPER_EXECUTED")
    set_milestone(cycle, "NORMALIZED_BATCH_CREATED")

    set_step(cycle, "wrapper", status="DONE", mode=mode,
             summary=f"Layout {wrapper_result.get('layout_id')} • {wrapper_result.get('rows_valid')} linhas válidas.")
    set_step(cycle, "normalization", status="DONE", mode=mode,
             summary=f"{wrapper_result.get('rows_valid')} registros normalizados, {wrapper_result.get('rows_rejected')} rejeitados.")
    save_cycle(cycle)
    return cycle


# ── Etapa 4: modelo canônico ────────────────────────────────────────────────
def run_ontology_step(cycle: dict, **_: Any) -> dict[str, Any]:
    ok, msg = can_run_ontology(cycle)
    if not ok:
        add_error(cycle, "ontology", msg)
        set_step(cycle, "ontology", status="ERROR")
        set_milestone(cycle, "FAILED")
        return cycle

    set_pipeline_progress(cycle, "ontology", "Populando ontologia / modelo canônico")
    set_step(cycle, "ontology", status="RUNNING")
    _emit_canonical(cycle, "CANONICAL_MODEL_POPULATION_STARTED", {}, include_legacy=False)

    ontology_result = ontology_adapter.publish_to_canonical_model(cycle.get("wrapper", {}))
    cycle["ontology"] = {k: v for k, v in ontology_result.items() if k != "_ontology"}
    if ontology_result.get("_ontology") is not None:
        _ONTOLOGY_CACHE[cycle["cycle_id"]] = ontology_result["_ontology"]
    mode = _mode_of(ontology_result)

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
    return cycle


# ── Etapa 5: validação semântica ────────────────────────────────────────────
def run_semantic_step(cycle: dict, **_: Any) -> dict[str, Any]:
    ok, msg = can_run_semantic_validation(cycle)
    if not ok:
        add_error(cycle, "semantic", msg)
        set_step(cycle, "semantic", status="ERROR")
        set_milestone(cycle, "FAILED")
        return cycle

    set_pipeline_progress(cycle, "semantic", "Validando semanticamente")
    set_step(cycle, "semantic", status="RUNNING")
    _emit_canonical(cycle, "SEMANTIC_VALIDATION_STARTED", {}, include_legacy=False)

    dataset = dict(cycle.get("ontology", {}))
    onto_obj = _ONTOLOGY_CACHE.get(cycle["cycle_id"])
    if onto_obj is not None:
        dataset["_ontology"] = onto_obj
    validation = ontology_adapter.run_semantic_validation(dataset)
    cycle["semantic_validation"] = validation
    mode = _mode_of(validation)
    critical = validation.get("critical_errors", 0)
    warns = validation.get("warnings", 0)

    _emit_canonical(cycle, "SEMANTIC_VALIDATION_COMPLETED", {"warnings": warns, "critical": critical}, include_legacy=False)
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
    return cycle


# ── Etapa 6: cálculo ────────────────────────────────────────────────────────
def run_calculation_step(cycle: dict, params: dict | None = None, **_: Any) -> dict[str, Any]:
    ok, msg = can_run_calculation(cycle)
    if not ok:
        add_error(cycle, "calculation", msg)
        set_step(cycle, "calculation", status="ERROR")
        set_milestone(cycle, "FAILED")
        return cycle

    set_pipeline_progress(cycle, "calculation", "Executando cálculo de emissões")
    set_step(cycle, "calculation", status="RUNNING")
    stored_params = cycle.get("calculation_params") or {}
    params = {**stored_params, **(params or {})}
    if "gwp" not in params:
        params["gwp"] = config.DEFAULT_GWP
    cycle["calculation_params"] = params

    _emit_canonical(cycle, "CALCULATION_EXECUTION_STARTED", {"gwp": params.get("gwp")}, include_legacy=False)

    calc_input = {
        **(cycle.get("ontology") or {}),
        "normalized_payload": cycle.get("normalized_data") or [],
        "wrapper": cycle.get("wrapper") or {},
        "calculation_params": params,
    }
    calculation = calculation_adapter.run_emission_calculation(calc_input, params)
    cycle["calculation"] = calculation
    mode = _mode_of(calculation)

    if cycle.get("canonical_snapshot_id") and cycle.get("reporting_period_id"):
        prov = provenance_adapter.record_calculation_flow(
            cycle["pipeline_run_id"], cycle["canonical_snapshot_id"],
            cycle["reporting_period_id"], calculation,
        )
        cycle["calculation_execution_id"] = prov.get("calculation_execution_id")
        cycle["calculation_result_set_id"] = prov.get("calculation_result_set_id")

    _emit_canonical(cycle, "CALCULATION_EXECUTED", {"co2e_total_kg": calculation.get("co2e_total_kg")}, include_legacy=False)
    _emit_canonical(cycle, "PRELIMINARY_RESULT_CREATED", {
        "co2e_total_kg": calculation.get("co2e_total_kg"),
        "preliminary_hash": calculation.get("preliminary_hash"),
    })
    _emit(cycle, "CALCULATION_PRELIMINARY_RESULT_CREATED", {"co2e_total_kg": calculation.get("co2e_total_kg")})
    set_milestone(cycle, "CALCULATION_EXECUTED")

    co2e = calculation.get("co2e_total_kg", 0)
    set_step(cycle, "calculation", status="DONE", mode=mode,
             summary=f"{co2e:,.1f} kg CO₂e • intensidade {calculation.get('co2e_intensity_per_milk_liter', 0):.3f} kg/L.")
    save_cycle(cycle)
    return cycle


# ── Etapa 7: aprovação humana ───────────────────────────────────────────────
def run_approval_step(cycle: dict, approval: dict | None = None, **_: Any) -> dict[str, Any]:
    if not cycle.get("calculation"):
        add_error(cycle, "approval", "Execute o cálculo primeiro.")
        set_step(cycle, "approval", status="ERROR")
        return cycle

    approval = approval or {"decision": "APPROVED", "approver": "Dr. Ana Souza",
                            "justification": "Aprovado via pipeline."}
    approval["approved_at"] = now_iso()
    cycle["approval"] = approval
    decision = approval.get("decision", "APPROVED")

    prov = {}
    if cycle.get("calculation_result_set_id") and cycle.get("reporting_period_id"):
        prov = provenance_adapter.record_approval(
            cycle["pipeline_run_id"], cycle["calculation_result_set_id"],
            cycle["reporting_period_id"], approval,
        )

    if decision == "APPROVED":
        _emit_canonical(cycle, "CALCULATION_APPROVED", {"decision": decision}, include_legacy=False)
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
    return cycle


# ── Etapa 8: publicação final ───────────────────────────────────────────────
def run_publication_step(cycle: dict, **_: Any) -> dict[str, Any]:
    ok, msg = can_publish_final_ontology(cycle)
    if not ok:
        add_error(cycle, "publication", msg)
        set_step(cycle, "publication", status="ERROR")
        return cycle

    set_step(cycle, "publication", status="RUNNING")
    _emit_canonical(cycle, "FINAL_ONTOLOGY_PUBLICATION_STARTED", {}, include_legacy=False)

    publication = {
        "ontology_version": f"final_ontology_{cycle['reporting_period']}_001",
        "published_at": now_iso(),
        "ontology_hash": (cycle.get("ontology") or {}).get("ontology_hash", ""),
        "methodology": (cycle.get("calculation") or {}).get("methodology", "IPCC/IDF-compatible"),
        "status": "PUBLISHED",
    }
    cycle["publication"] = publication
    prov = {}
    if cycle.get("calculation_result_set_id"):
        prov = provenance_adapter.record_publication(
            cycle["pipeline_run_id"], cycle["calculation_result_set_id"], publication
        )

    _emit_canonical(cycle, "FINAL_ONTOLOGY_PUBLISHED", {"version": publication["ontology_version"]}, include_legacy=False)
    _emit(cycle, "FINAL_ONTOLOGY_PUBLISHED", {"version": publication["ontology_version"]})
    set_milestone(cycle, "FINAL_ONTOLOGY_PUBLISHED")
    set_milestone(cycle, "BLOCKCHAIN_UNLOCKED")

    set_step(cycle, "publication", status="DONE", mode=_mode_of(prov),
             summary=f"Ontologia {publication['ontology_version']} publicada.")
    save_cycle(cycle)
    return cycle


# ── Etapa 9: pacote de evidências ───────────────────────────────────────────
def run_evidence_step(cycle: dict, **_: Any) -> dict[str, Any]:
    ok, msg = can_unlock_blockchain(cycle)
    if not ok:
        add_error(cycle, "evidence", f"Blockchain bloqueado: {msg}")
        set_step(cycle, "evidence", status="ERROR")
        return cycle

    set_step(cycle, "evidence", status="RUNNING")
    cycle["hashes"] = blockchain_adapter.compute_local_hashes(cycle)
    _emit_canonical(cycle, "ARTIFACT_HASHES_CREATED", {"hashes": list(cycle["hashes"].keys())}, include_legacy=False)

    try:
        evidence = blockchain_adapter.create_evidence_package(cycle)
    except Exception as exc:
        add_error(cycle, "evidence", f"Falha ao construir pacote: {exc}")
        set_step(cycle, "evidence", status="ERROR")
        save_cycle(cycle)
        return cycle

    cycle["evidence_package"] = evidence
    mode = _mode_of(evidence)
    _emit_canonical(cycle, "EVIDENCE_PACKAGE_CREATED", {"package_id": evidence.get("evidence_package_id")}, include_legacy=False)
    _emit(cycle, "EVIDENCE_PACKAGE_CREATED", {"package_id": evidence.get("evidence_package_id")})
    _emit_canonical(cycle, "MERKLE_ROOT_CREATED", {"merkle_root": evidence.get("merkle_root")})
    _emit(cycle, "LOCAL_HASH_CREATED", {"merkle_root": evidence.get("merkle_root")})
    set_milestone(cycle, "EVIDENCE_PACKAGE_CREATED")
    set_milestone(cycle, "MERKLE_ROOT_CREATED")

    set_step(cycle, "evidence", status="DONE", mode=mode,
             summary=f"Pacote {str(evidence.get('evidence_package_id'))[:12]}… • Merkle {str(evidence.get('merkle_root',''))[:12]}…")
    save_cycle(cycle)
    return cycle


# ── Etapa 10: blockchain (ancoragem) ────────────────────────────────────────
def run_anchoring_step(cycle: dict, **_: Any) -> dict[str, Any]:
    ok, msg = can_unlock_blockchain(cycle)
    if not ok:
        add_error(cycle, "blockchain", f"Blockchain bloqueado: {msg}")
        set_step(cycle, "blockchain", status="ERROR")
        return cycle
    if not cycle.get("evidence_package"):
        add_error(cycle, "blockchain", "Construa o pacote de evidências primeiro.")
        set_step(cycle, "blockchain", status="ERROR")
        return cycle

    set_step(cycle, "blockchain", status="RUNNING")
    pkg_id = cycle["evidence_package"].get("evidence_package_id", "")
    _emit_canonical(cycle, "ANCHOR_REQUEST_CREATED", {"package_id": pkg_id}, include_legacy=False)

    try:
        anchor = blockchain_adapter.simulate_anchoring(pkg_id)
    except Exception as exc:
        add_error(cycle, "blockchain", f"Falha na ancoragem: {exc}")
        set_step(cycle, "blockchain", status="ERROR")
        save_cycle(cycle)
        return cycle

    cycle["anchoring"] = anchor
    cycle["evidence_package"]["anchoring_status"] = "ANCHORING_SIMULATED"
    cycle["evidence_package"]["transaction_id"] = anchor.get("transaction_id")
    cycle["evidence_package"]["block_number"] = anchor.get("block_number")
    mode = _mode_of(anchor)

    _emit_canonical(cycle, "ANCHORING_SIMULATED", {"tx": anchor.get("transaction_id")}, include_legacy=False)
    _emit(cycle, "ANCHORING_SIMULATED", {"tx": anchor.get("transaction_id")})
    set_milestone(cycle, "ANCHORING_SIMULATED")

    set_step(cycle, "blockchain", status="ANCHORED", mode=mode,
             summary=f"Ancorado (simulado) • tx {str(anchor.get('transaction_id',''))[:14]}…")
    save_cycle(cycle)
    return cycle


# ── Etapa 11: verificação ───────────────────────────────────────────────────
def run_verification_step(cycle: dict, tamper: bool = False, **_: Any) -> dict[str, Any]:
    ok, msg = can_unlock_blockchain(cycle)
    if not ok:
        add_error(cycle, "verification", f"Blockchain bloqueado: {msg}")
        set_step(cycle, "verification", status="ERROR")
        return cycle
    if not cycle.get("evidence_package"):
        add_error(cycle, "verification", "Construa e ancore o pacote primeiro.")
        set_step(cycle, "verification", status="ERROR")
        return cycle

    set_step(cycle, "verification", status="RUNNING")
    integrity = blockchain_adapter.verify_integrity(cycle.get("evidence_package", {}), {"tamper": tamper})
    cycle["integrity"] = integrity
    mode = _mode_of(integrity)

    _emit_canonical(cycle, "INTEGRITY_VERIFICATION_EXECUTED", {"is_valid": integrity.get("is_valid")}, include_legacy=False)
    _emit(cycle, "VERIFICATION_EXECUTED", {"is_valid": integrity.get("is_valid")})
    set_milestone(cycle, "INTEGRITY_VERIFICATION_EXECUTED")

    if integrity.get("is_valid"):
        _emit_canonical(cycle, "PROVENANCE_CHAIN_VERIFIED", {"cycle_id": cycle.get("cycle_id")}, include_legacy=False)
        set_milestone(cycle, "PROVENANCE_CHAIN_VERIFIED")
        set_milestone(cycle, "VERIFIED")
        set_step(cycle, "verification", status="VERIFIED", mode=mode, summary="Pacote íntegro.")
    else:
        set_step(cycle, "verification", status="DIVERGENT", mode=mode, summary="Divergência detectada.")
    save_cycle(cycle)
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
        return cycle

    cycle = run_wrapper_step(cycle, layout_name)
    if cycle.get("steps", {}).get("wrapper", {}).get("status") == "ERROR":
        return cycle

    cycle = run_ontology_step(cycle)
    if cycle.get("steps", {}).get("ontology", {}).get("status") == "ERROR":
        return cycle

    cycle = run_semantic_step(cycle)
    if cycle.get("steps", {}).get("semantic", {}).get("status") == "ERROR":
        return cycle

    cycle = run_calculation_step(cycle, calculation_params)
    if cycle.get("steps", {}).get("calculation", {}).get("status") == "ERROR":
        return cycle

    if mark_pending:
        cycle = mark_pending_approval(cycle)
        set_pipeline_progress(cycle, "pending", "Aguardando aprovação humana")
    save_cycle(cycle)
    return cycle


def run_auto_pipeline_after_approval(cycle: dict, approval: dict) -> dict[str, Any]:
    """Continua automaticamente após decisão humana."""
    decision = approval.get("decision", "APPROVED")
    cycle = run_approval_step(cycle, approval)

    if decision != "APPROVED":
        cycle.pop("publication", None)
        cycle.pop("evidence_package", None)
        cycle.pop("anchoring", None)
        cycle.pop("integrity", None)
        cycle["hashes"] = {}
        save_cycle(cycle)
        return cycle

    cycle = run_publication_step(cycle)
    if cycle.get("steps", {}).get("publication", {}).get("status") == "ERROR":
        return cycle

    cycle = run_evidence_step(cycle)
    if cycle.get("steps", {}).get("evidence", {}).get("status") == "ERROR":
        return cycle

    cycle = run_anchoring_step(cycle)
    if cycle.get("steps", {}).get("blockchain", {}).get("status") == "ERROR":
        return cycle

    cycle = run_verification_step(cycle)
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
