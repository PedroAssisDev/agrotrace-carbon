"""Estado central tipado do EmissionCycle.

Define o schema único do ciclo, os rótulos amigáveis de status e o registry
das 11 etapas do pipeline. Tanto o orquestrador quanto as telas leem deste
módulo para garantir consistência.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from services.provenance_event_catalog import all_event_names, canonical_event_type
from utils.date_helpers import now_iso


# ── Status técnico → rótulo amigável ────────────────────────────────────────
STATUS_LABELS: dict[str, str] = {
    "PENDING": "Pendente",
    "RUNNING": "Em execução",
    "DONE": "Concluído",
    "DONE_WARNINGS": "Concluído com alertas",
    "ERROR": "Erro",
    "AWAITING_APPROVAL": "Aguardando aprovação",
    "APPROVED": "Aprovado",
    "ANCHORED": "Ancorado",
    "VERIFIED": "Verificado",
    "DIVERGENT": "Divergente",
}

STATUS_COLORS: dict[str, str] = {
    "PENDING": "secondary",
    "RUNNING": "info",
    "DONE": "success",
    "DONE_WARNINGS": "warning",
    "ERROR": "danger",
    "AWAITING_APPROVAL": "warning",
    "APPROVED": "success",
    "ANCHORED": "primary",
    "VERIFIED": "success",
    "DIVERGENT": "danger",
}

# Marcos principais do ciclo (current_status)
PIPELINE_MILESTONES: tuple[str, ...] = (
    "DRAFT",
    "RAW_DATA_RECEIVED",
    "ORIGINAL_FILE_STORED",
    "RAW_FILE_HASH_CREATED",
    "RAW_DATA_REGISTERED",
    "WRAPPER_EXECUTED",
    "NORMALIZED_BATCH_CREATED",
    "CANONICAL_MODEL_POPULATED",
    "SEMANTIC_VALIDATION_COMPLETED",
    "CALCULATION_EXECUTED",
    "AWAITING_HUMAN_APPROVAL",
    "CALCULATION_APPROVED",
    "FINAL_ONTOLOGY_PUBLISHED",
    "BLOCKCHAIN_UNLOCKED",
    "EVIDENCE_PACKAGE_CREATED",
    "MERKLE_ROOT_CREATED",
    "ANCHORING_SIMULATED",
    "INTEGRITY_VERIFICATION_EXECUTED",
    "PROVENANCE_CHAIN_VERIFIED",
    "VERIFIED",
    "REJECTED",
    "CORRECTION_REQUESTED",
    "FAILED",
)

# Fases exibidas durante automação pós-upload
AUTO_PIPELINE_PHASES: list[tuple[str, str, str]] = [
    ("raw", "Processando upload e salvando arquivo original", "raw_data"),
    ("hash", "Calculando hash SHA-256", "raw_data"),
    ("wrapper", "Executando wrapper", "wrapper"),
    ("normalized", "Gerando lote normalizado", "normalization"),
    ("ontology", "Populando ontologia / modelo canônico", "ontology"),
    ("semantic", "Validando semanticamente", "semantic"),
    ("calculation", "Executando cálculo de emissões", "calculation"),
    ("pending", "Resultado preliminar — aguardando aprovação humana", "approval"),
]


def status_label(status: str | None) -> str:
    if not status:
        return STATUS_LABELS["PENDING"]
    return STATUS_LABELS.get(status, status.replace("_", " ").title())


def status_color(status: str | None) -> str:
    if not status:
        return STATUS_COLORS["PENDING"]
    return STATUS_COLORS.get(status, "secondary")


def set_milestone(cycle: dict, milestone: str) -> None:
    """Atualiza marco principal do ciclo."""
    cycle["current_status"] = milestone
    cycle["updated_at"] = now_iso()


def set_pipeline_progress(cycle: dict, phase: str, label: str) -> None:
    cycle["pipeline_progress"] = {"phase": phase, "label": label, "at": now_iso()}
    cycle["updated_at"] = now_iso()


# ── Registry das 11 etapas ──────────────────────────────────────────────────
@dataclass(frozen=True)
class StepDef:
    step_id: str
    label: str
    description: str
    orchestrator_fn: str
    events: tuple[str, ...] = ()
    needs_input: bool = False


PIPELINE_STEP_DEFS: list[StepDef] = [
    StepDef(
        "raw_data",
        "1. Dados Brutos",
        "Upload e registro do arquivo bruto (original) com hash SHA-256.",
        "register_raw_upload",
        (
            "RAW_DATA_REGISTERED",
            "RAW_DATA_UPLOADED",
            "RAW_DATA_RECEIVED",
            "ORIGINAL_FILE_STORED",
            "RAW_FILE_HASH_CREATED",
        ),
        needs_input=True,
    ),
    StepDef(
        "wrapper",
        "2. Wrapper",
        "Execução do wrapper para padronizar o arquivo bruto.",
        "run_wrapper_step",
        ("WRAPPER_EXECUTION_STARTED", "WRAPPER_EXECUTED"),
    ),
    StepDef(
        "normalization",
        "3. Normalização",
        "Lote normalizado gerado a partir do wrapper.",
        "run_wrapper_step",
        ("NORMALIZED_BATCH_CREATED", "NORMALIZED_DATA_DERIVED_FROM_RAW_DATA"),
    ),
    StepDef(
        "ontology",
        "4. Modelo Canônico",
        "População do modelo canônico (ontologia) com os dados normalizados.",
        "run_ontology_step",
        (
            "CANONICAL_MODEL_POPULATION_STARTED",
            "CANONICAL_MODEL_POPULATED",
            "SEMANTIC_MAPPING_COMPLETED",
            "CANONICAL_PUBLISHED",
        ),
    ),
    StepDef(
        "semantic",
        "5. Validação Semântica",
        "Validação semântica do modelo canônico.",
        "run_semantic_step",
        ("SEMANTIC_VALIDATION_STARTED", "SEMANTIC_VALIDATION_COMPLETED"),
    ),
    StepDef(
        "calculation",
        "6. Cálculo",
        "Cálculo das emissões GHG (kg CO₂e).",
        "run_calculation_step",
        (
            "CALCULATION_EXECUTION_STARTED",
            "CALCULATION_EXECUTED",
            "PRELIMINARY_RESULT_CREATED",
            "CALCULATION_PRELIMINARY_RESULT_CREATED",
        ),
    ),
    StepDef(
        "approval",
        "7. Aprovação Humana",
        "Revisão e aprovação humana do resultado preliminar.",
        "run_approval_step",
        ("HUMAN_APPROVAL_REQUESTED", "CALCULATION_APPROVED"),
        needs_input=True,
    ),
    StepDef(
        "publication",
        "8. Publicação Final",
        "Publicação do manifesto final aprovado (artefato imutável).",
        "run_publication_step",
        ("APPROVED_RESULT_PUBLISHED", "FINAL_ONTOLOGY_PUBLISHED"),
    ),
    StepDef(
        "evidence",
        "9. Pacote de Evidências",
        "Construção do pacote de evidências com Merkle Root.",
        "run_evidence_step",
        ("EVIDENCE_PACKAGE_CREATED", "ARTIFACT_HASHES_CREATED", "MERKLE_ROOT_CREATED", "LOCAL_HASH_CREATED"),
    ),
    StepDef(
        "blockchain",
        "10. Blockchain",
        "Ancoragem (simulada) do pacote de evidências.",
        "run_anchoring_step",
        ("ANCHOR_REQUEST_CREATED", "ANCHORING_SIMULATED", "BLOCKCHAIN_ANCHOR_CREATED"),
    ),
    StepDef(
        "verification",
        "11. Verificação",
        "Verificação de imutabilidade comparando hashes.",
        "run_verification_step",
        ("INTEGRITY_VERIFICATION_EXECUTED", "VERIFICATION_EXECUTED", "PROVENANCE_CHAIN_VERIFIED"),
    ),
]

STEP_IDS: list[str] = [s.step_id for s in PIPELINE_STEP_DEFS]
STEP_BY_ID: dict[str, StepDef] = {s.step_id: s for s in PIPELINE_STEP_DEFS}


def step_index(step_id: str) -> int:
    return STEP_IDS.index(step_id) if step_id in STEP_IDS else -1


def _expanded_event_types(events: tuple[str, ...]) -> set[str]:
    expanded: set[str] = set()
    for ev in events:
        expanded.update(all_event_names(ev))
    return expanded


# ── Schema do ciclo ─────────────────────────────────────────────────────────
def new_cycle(
    property_id: str,
    property_name: str,
    reporting_period: str,
    *,
    frequency: str | None = None,
    layout_id: str | None = None,
    uploaded_by: str | None = None,
    calculation_params: dict | None = None,
) -> dict[str, Any]:
    """Cria a estrutura central de um EmissionCycle vazio."""
    steps = {
        s.step_id: {
            "status": "PENDING",
            "mode": None,
            "summary": None,
            "started_at": None,
            "finished_at": None,
        }
        for s in PIPELINE_STEP_DEFS
    }
    return {
        "cycle_id": f"CYCLE-{uuid.uuid4().hex[:12].upper()}",
        "property_id": property_id,
        "property_name": property_name,
        "reporting_period": reporting_period,
        "frequency": frequency or "monthly",
        "layout_id": layout_id,
        "uploaded_by": uploaded_by or "frontend@agrotrace",
        "calculation_params": calculation_params or {},
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "current_status": "DRAFT",
        "current_step": STEP_IDS[0],
        "pipeline_progress": None,
        "demo_mode": False,
        # Identificadores de proveniência
        "pipeline_run_id": None,
        "reporting_period_id": None,
        "source_artifact_id": None,
        "normalized_batch_id": None,
        "canonical_snapshot_id": None,
        "calculation_execution_id": None,
        "calculation_result_set_id": None,
        # Artefatos por etapa
        "raw_file": None,
        "wrapper": None,
        "normalized_data": [],
        "ontology": None,
        "semantic_validation": None,
        "calculation": None,
        "approval": None,
        "publication": None,
        "hashes": {},
        "evidence_package": None,
        "anchoring": None,
        "integrity": None,
        # Estado por etapa e mensagens
        "steps": steps,
        "provenance_events": [],
        "errors": [],
        "warnings": [],
    }


def set_step(
    cycle: dict,
    step_id: str,
    *,
    status: str,
    mode: str | None = None,
    summary: str | None = None,
) -> None:
    """Atualiza o estado de uma etapa do ciclo."""
    step = cycle.setdefault("steps", {}).setdefault(step_id, {})
    if status == "RUNNING" and not step.get("started_at"):
        step["started_at"] = now_iso()
    if status in {"DONE", "DONE_WARNINGS", "ERROR", "APPROVED", "ANCHORED", "VERIFIED", "DIVERGENT"}:
        step["finished_at"] = now_iso()
    step["status"] = status
    if mode is not None:
        step["mode"] = mode
    if summary is not None:
        step["summary"] = summary
    cycle["current_step"] = step_id
    cycle["updated_at"] = now_iso()


def add_error(cycle: dict, step_id: str, message: str) -> None:
    cycle.setdefault("errors", []).append({"step": step_id, "message": message, "at": now_iso()})


def add_warning(cycle: dict, step_id: str, message: str) -> None:
    cycle.setdefault("warnings", []).append({"step": step_id, "message": message, "at": now_iso()})


def is_step_done(cycle: dict, step_id: str) -> bool:
    status = cycle.get("steps", {}).get(step_id, {}).get("status")
    return status in {"DONE", "DONE_WARNINGS", "APPROVED", "ANCHORED", "VERIFIED"}


def completed_count(cycle: dict) -> int:
    return sum(1 for s in STEP_IDS if is_step_done(cycle, s))


def progress_pct(cycle: dict) -> int:
    total = len(STEP_IDS)
    return int(round(100 * completed_count(cycle) / total)) if total else 0


def step_label_for_event(event_type: str) -> str:
    """Rótulo amigável da etapa associada a um event_type de proveniência."""
    normalized = canonical_event_type(event_type)
    for step_def in PIPELINE_STEP_DEFS:
        if event_type in step_def.events or normalized in step_def.events:
            return step_def.label
        expanded = _expanded_event_types(step_def.events)
        if event_type in expanded or normalized in expanded:
            return step_def.label
    return "—"


def events_for_step(cycle: dict, step_id: str) -> list[dict]:
    """Eventos de proveniência vinculados a uma etapa do pipeline."""
    step_def = STEP_BY_ID.get(step_id)
    if not step_def:
        return []
    types = _expanded_event_types(step_def.events)
    return [
        e for e in cycle.get("provenance_events", [])
        if e.get("event_type") in types or canonical_event_type(e.get("event_type", "")) in types
    ]


def events_for_cycle(events: list[dict], cycle_id: str, cycle: dict) -> list[dict]:
    """Filtra eventos por aggregate_id, cycle_id no payload ou pipeline_run_id."""
    filtered = [
        e for e in events
        if str(e.get("aggregate_id")) == str(cycle_id)
        or (e.get("payload_json") or {}).get("cycle_id") == cycle_id
        or (e.get("payload") or {}).get("cycle_id") == cycle_id
        or str(e.get("pipeline_execution_id")) == str(cycle.get("pipeline_run_id"))
    ]
    return filtered or events
