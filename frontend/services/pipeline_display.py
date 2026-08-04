"""Camada de apresentação da pipeline — 18 etapas visuais (orquestrador mantém 11)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Phase = Literal["operational", "blockchain", "audit"]


@dataclass(frozen=True)
class DisplayStep:
    step_num: int
    step_key: str
    label: str
    phase: Phase
    service: str
    canonical_events: tuple[str, ...]
    orchestrator_step_id: str
    blockchain_zone: bool = False


DISPLAY_PIPELINE_STEPS: list[DisplayStep] = [
    DisplayStep(1, "raw_upload", "Dado Bruto", "operational", "Frontend", ("RAW_DATA_RECEIVED", "RAW_DATA_UPLOADED"), "raw_data"),
    DisplayStep(2, "original_file", "Arquivo Original", "operational", "save-file / local", ("ORIGINAL_FILE_STORED",), "raw_data"),
    DisplayStep(3, "raw_hash", "Hash do Arquivo", "operational", "hash utility", ("RAW_FILE_HASH_CREATED",), "raw_data"),
    DisplayStep(4, "raw_prov", "Proveniência Inicial", "operational", "traceability-service", ("RAW_DATA_REGISTERED",), "raw_data"),
    DisplayStep(5, "wrapper", "Wrapper", "operational", "wrappers-service", ("WRAPPER_EXECUTION_STARTED", "WRAPPER_EXECUTED"), "wrapper"),
    DisplayStep(6, "normalized", "Dado Normalizado", "operational", "wrappers-service", ("NORMALIZED_BATCH_CREATED",), "normalization"),
    DisplayStep(7, "derivation", "Derivação Normalizado", "operational", "traceability-service", ("NORMALIZED_DATA_DERIVED_FROM_RAW_DATA",), "normalization"),
    DisplayStep(8, "canonical", "Modelo Canônico", "operational", "ontology-manager", ("CANONICAL_MODEL_POPULATION_STARTED", "CANONICAL_MODEL_POPULATED", "CANONICAL_PUBLISHED"), "ontology"),
    DisplayStep(9, "semantic", "Validação Semântica", "operational", "ontology-manager", ("SEMANTIC_VALIDATION_STARTED", "SEMANTIC_VALIDATION_COMPLETED"), "semantic"),
    DisplayStep(10, "calculation", "Cálculo", "operational", "calculation-service", ("CALCULATION_EXECUTION_STARTED", "CALCULATION_EXECUTED"), "calculation"),
    DisplayStep(11, "preliminary", "Resultado Preliminar", "operational", "calculation-service", ("PRELIMINARY_RESULT_CREATED", "CALCULATION_PRELIMINARY_RESULT_CREATED"), "calculation"),
    DisplayStep(12, "approval", "Aprovação Humana", "operational", "Frontend + traceability", ("HUMAN_APPROVAL_REQUESTED", "CALCULATION_APPROVED"), "approval"),
    DisplayStep(13, "publication", "Publicação Final", "operational", "publication_service", ("APPROVED_RESULT_PUBLISHED", "FINAL_ONTOLOGY_PUBLISHED", "FINAL_ONTOLOGY_PUBLICATION_STARTED"), "publication"),
    DisplayStep(14, "evidence", "Pacote de Evidências", "blockchain", "blockchain-service", ("EVIDENCE_PACKAGE_CREATED",), "evidence", True),
    DisplayStep(15, "artifact_hashes", "Hashes Finais", "blockchain", "blockchain-service", ("ARTIFACT_HASHES_CREATED", "LOCAL_HASH_CREATED"), "evidence", True),
    DisplayStep(16, "merkle", "Merkle Root", "blockchain", "blockchain-service", ("MERKLE_ROOT_CREATED",), "evidence", True),
    DisplayStep(17, "anchoring", "Ancoragem", "blockchain", "blockchain-service", ("ANCHOR_REQUEST_CREATED", "ANCHORING_SIMULATED", "BLOCKCHAIN_ANCHOR_CREATED", "BLOCKCHAIN_ANCHORED"), "blockchain", True),
    DisplayStep(18, "verification", "Verificação", "blockchain", "blockchain-service", ("INTEGRITY_VERIFICATION_EXECUTED", "VERIFICATION_EXECUTED", "INTEGRITY_VERIFIED"), "verification", True),
]

AUDIT_STEP = DisplayStep(19, "prov_audit", "Proveniência Completa", "audit", "traceability-service", ("PROVENANCE_CHAIN_VERIFIED",), "verification")

BLOCKCHAIN_GATE_AFTER = 13


def display_status_for_step(cycle: dict, display_step: DisplayStep) -> str:
    """Resolve status visual a partir do step do orquestrador."""
    steps = cycle.get("steps") or {}
    orch = steps.get(display_step.orchestrator_step_id, {})
    return orch.get("status", "PENDING")


def events_for_display_step(cycle: dict, display_step: DisplayStep) -> list[dict]:
    """Filtra provenance_events do ciclo pelos eventos canônicos da etapa visual."""
    wanted = set(display_step.canonical_events)
    return [e for e in (cycle.get("provenance_events") or []) if e.get("event_type") in wanted]
