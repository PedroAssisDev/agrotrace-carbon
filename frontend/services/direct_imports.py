"""Centraliza imports diretos dos serviços locais existentes."""

from __future__ import annotations

import logging

from services.bootstrap import bootstrap_all

logger = logging.getLogger("agrotrace.imports")

# Garante paths antes dos imports
bootstrap_all()

# ── Wrappers ────────────────────────────────────────────────────────────────
try:
    from wrappers import process_file
    from wrappers.contracts import ProcessingResult, ProcessingStatus
except Exception as exc:
    logger.warning("wrappers indisponível: %s", exc)
    process_file = None
    ProcessingResult = None
    ProcessingStatus = None

# ── Cálculos ─────────────────────────────────────────────────────────────────
try:
    from emissions.defaults import gwp_ipcc_ar4
    from emissions.explanation import build_calculation_explanation, explanation_from_dict
    from emissions.farm_period import FarmPeriodInput
    from emissions.temporal_scope import TemporalScope
    from orchestration.pipeline import compute_farm_period_emissions, compute_row_emissions
except Exception as exc:
    logger.warning("calculation-service indisponível: %s", exc)
    gwp_ipcc_ar4 = None
    build_calculation_explanation = None
    explanation_from_dict = None
    FarmPeriodInput = None
    TemporalScope = None
    compute_farm_period_emissions = None
    compute_row_emissions = None

# ── Ontologia ─────────────────────────────────────────────────────────────────
try:
    from ontology import (
        build_full_ontology,
        export_ontology,
        populate_from_dataframe,
        set_groups_status,
        set_parameter_status,
        upsert_emission_factor_value,
        upsert_gwp_value,
        upsert_emission_cycle,
        upsert_emission_result,
        upsert_observation,
        upsert_property,
        set_results_status,
        set_cycle_status,
    )
    from ontology.validators import validate_all
except Exception as exc:
    logger.warning("ontology-manager indisponível: %s", exc)
    build_full_ontology = None
    export_ontology = None
    populate_from_dataframe = None
    validate_all = None
    upsert_emission_factor_value = None
    upsert_gwp_value = None
    set_parameter_status = None
    set_groups_status = None
    upsert_emission_cycle = None
    upsert_emission_result = None
    upsert_observation = None
    upsert_property = None
    set_results_status = None
    set_cycle_status = None

# ── Proveniência ──────────────────────────────────────────────────────────────
try:
    from provenance_service.application.services import (
        ProvenanceRecorder,
        RecordBlockchainAnchorCommand,
        RecordCalculationExecutionCommand,
        RecordCalculationMethodCommand,
        RecordCalculationMethodVersionCommand,
        RecordCalculationParameterSetCommand,
        RecordCalculationResultSetCommand,
        RecordCalculationReviewCommand,
        RecordCanonicalSnapshotCommand,
        RecordHashCommand,
        ConfirmBlockchainAnchorCommand,
        RecordIntegrityVerificationCommand,
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
    ConfirmBlockchainAnchorCommand = None
    RecordIntegrityVerificationCommand = None
    RecordBlockchainAnchorCommand = None
    ResultItemInput = None
    ParameterValueInput = None
    RecordCalculationMethodCommand = None
    RecordCalculationMethodVersionCommand = None
    RecordCalculationParameterSetCommand = None

# ── Blockchain ────────────────────────────────────────────────────────────────
try:
    from app.application.container import ServiceContainer, init_database
    from app.application.dto.commands import (
        AnchorEvidencePackageCommand,
        BuildEvidencePackageCommand,
        ObserveEventsCommand,
        QueryAnchoredEvidenceCommand,
        SimulateAnchoringCommand,
        VerifyAnchoredEvidenceCommand,
        VerifyEvidencePackageCommand,
    )
    from app.application.use_cases.anchor_evidence_package import AnchorEvidencePackageUseCase
    from app.application.use_cases.build_evidence_package import BuildEvidencePackageUseCase
    from app.application.use_cases.observe_provenance_events import ObserveProvenanceEventsUseCase
    from app.application.use_cases.query_anchored_evidence import QueryAnchoredEvidenceUseCase
    from app.application.use_cases.simulate_anchoring import SimulateAnchoringUseCase
    from app.application.use_cases.verify_anchored_evidence import VerifyAnchoredEvidenceUseCase
    from app.application.use_cases.verify_evidence_package import VerifyEvidencePackageUseCase
    from app.domain.services.canonical_json_service import to_canonical_json
    from app.domain.services.merkle_service import build_merkle_root
    from app.domain.services.sha256_service import sha256_hex
except Exception as exc:
    logger.warning("blockchain-service indisponível: %s", exc)
    ServiceContainer = None
    init_database = None
    ObserveEventsCommand = None
    BuildEvidencePackageCommand = None
    SimulateAnchoringCommand = None
    AnchorEvidencePackageCommand = None
    QueryAnchoredEvidenceCommand = None
    VerifyAnchoredEvidenceCommand = None
    VerifyEvidencePackageCommand = None
    ObserveProvenanceEventsUseCase = None
    BuildEvidencePackageUseCase = None
    SimulateAnchoringUseCase = None
    AnchorEvidencePackageUseCase = None
    QueryAnchoredEvidenceUseCase = None
    VerifyAnchoredEvidenceUseCase = None
    VerifyEvidencePackageUseCase = None
    sha256_hex = None
    build_merkle_root = None
    to_canonical_json = None


def availability() -> dict[str, bool]:
    """Retorna disponibilidade de cada serviço."""
    return {
        "wrappers": process_file is not None,
        "calculations": compute_farm_period_emissions is not None,
        "ontology": build_full_ontology is not None,
        "provenance": ProvenanceRecorder is not None,
        "blockchain": ObserveProvenanceEventsUseCase is not None,
    }
