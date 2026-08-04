"""Centraliza imports diretos dos serviços locais existentes."""

from __future__ import annotations

import logging

from services.bootstrap import bootstrap_all

logger = logging.getLogger("agrotrace.imports")

# Garante paths antes dos imports
bootstrap_all()

# ── Wrappers ────────────────────────────────────────────────────────────────
try:
    from wrappers import process_file, process_file_auto
    from wrappers.contracts import ProcessingResult, ProcessingStatus
except Exception as exc:
    logger.warning("wrappers indisponível: %s", exc)
    process_file = None
    process_file_auto = None
    ProcessingResult = None
    ProcessingStatus = None

# ── Cálculos ─────────────────────────────────────────────────────────────────
try:
    from emissions.defaults import gwp_ipcc_ar4
    from emissions.farm_period import FarmPeriodInput
    from emissions.temporal_scope import TemporalScope
    from orchestration.pipeline import compute_farm_period_emissions, compute_row_emissions
except Exception as exc:
    logger.warning("calculation-service indisponível: %s", exc)
    gwp_ipcc_ar4 = None
    FarmPeriodInput = None
    TemporalScope = None
    compute_farm_period_emissions = None
    compute_row_emissions = None

# ── Ontologia ─────────────────────────────────────────────────────────────────
try:
    from ontology import build_full_ontology, export_ontology, populate_from_dataframe
    from ontology.validators import validate_all
except Exception as exc:
    logger.warning("ontology-manager indisponível: %s", exc)
    build_full_ontology = None
    export_ontology = None
    populate_from_dataframe = None
    validate_all = None

# ── Proveniência ──────────────────────────────────────────────────────────────
try:
    from provenance_service.application.services import (
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
        RecordReportingPeriodCommand,
        RecordResultPublicationCommand,
        RecordSemanticIntegrationCommand,
        RecordSourceArtifactCommand,
        RecordWrapperDefinitionCommand,
        RecordWrapperExecutionCommand,
        StartPipelineRunCommand,
    )
    from provenance_service.application.services.provenance_recorder import (
        ParameterValueInput,
        ResultItemInput,
    )
    from provenance_service.application.use_cases import ListOutboxEvents, ListOutboxEventsQuery
    from provenance_service.interfaces.api.deps import get_uow_factory
except Exception as exc:
    logger.warning("traceability-service indisponível: %s", exc)
    ProvenanceRecorder = None
    get_uow_factory = None
    ListOutboxEvents = None
    ListOutboxEventsQuery = None
    StartPipelineRunCommand = None
    RecordReportingPeriodCommand = None
    RecordSourceArtifactCommand = None
    RecordWrapperDefinitionCommand = None
    RecordWrapperExecutionCommand = None
    RecordNormalizedBatchCommand = None
    RecordSemanticIntegrationCommand = None
    RecordCanonicalSnapshotCommand = None
    RecordCalculationMethodCommand = None
    RecordCalculationMethodVersionCommand = None
    RecordCalculationParameterSetCommand = None
    RecordCalculationExecutionCommand = None
    RecordCalculationResultSetCommand = None
    RecordCalculationReviewCommand = None
    RecordResultPublicationCommand = None
    RecordHashCommand = None
    ResultItemInput = None
    ParameterValueInput = None
    RecordCalculationMethodCommand = None
    RecordCalculationMethodVersionCommand = None
    RecordCalculationParameterSetCommand = None

# ── Blockchain ────────────────────────────────────────────────────────────────
try:
    from app.application.container import ServiceContainer, init_database
    from app.application.dto.commands import (
        BuildEvidencePackageCommand,
        ObserveEventsCommand,
        SimulateAnchoringCommand,
        VerifyEvidencePackageCommand,
    )
    from app.application.use_cases.build_evidence_package import BuildEvidencePackageUseCase
    from app.application.use_cases.observe_provenance_events import ObserveProvenanceEventsUseCase
    from app.application.use_cases.simulate_anchoring import SimulateAnchoringUseCase
    from app.application.use_cases.verify_evidence_package import VerifyEvidencePackageUseCase
    from app.domain.services.merkle_service import build_merkle_root
    from app.domain.services.sha256_service import sha256_hex
except Exception as exc:
    logger.warning("blockchain-service indisponível: %s", exc)
    ServiceContainer = None
    init_database = None
    ObserveEventsCommand = None
    BuildEvidencePackageCommand = None
    SimulateAnchoringCommand = None
    VerifyEvidencePackageCommand = None
    ObserveProvenanceEventsUseCase = None
    BuildEvidencePackageUseCase = None
    SimulateAnchoringUseCase = None
    VerifyEvidencePackageUseCase = None
    sha256_hex = None
    build_merkle_root = None


def availability() -> dict[str, bool]:
    """Retorna disponibilidade de cada serviço."""
    return {
        "wrappers": process_file is not None,
        "calculations": compute_farm_period_emissions is not None,
        "ontology": build_full_ontology is not None,
        "provenance": ProvenanceRecorder is not None,
        "blockchain": ObserveProvenanceEventsUseCase is not None,
    }
