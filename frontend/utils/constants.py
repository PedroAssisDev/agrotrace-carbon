"""Constantes reutilizáveis na UI."""

from __future__ import annotations

# Status → variante CSS (.badge-status-{variante})
STATUS_VARIANTS = {
    "DRAFT": "pendente",
    "RAW_DATA_REGISTERED": "em-execucao",
    "ORIGINAL_FILE_STORED": "em-execucao",
    "WRAPPER_EXECUTED": "em-execucao",
    "NORMALIZED_BATCH_CREATED": "em-execucao",
    "CANONICAL_PUBLISHED": "publicado",
    "SEMANTIC_VALIDATION_APPROVED": "verificado",
    "SEMANTIC_VALIDATION_FAILED": "erro",
    "CALCULATION_PRELIMINARY_RESULT_CREATED": "em-execucao",
    "AWAITING_HUMAN_APPROVAL": "aguardando-aprovacao",
    "AWAITING_APPROVAL": "aguardando-aprovacao",
    "CALCULATION_APPROVED": "aprovado",
    "FINAL_ONTOLOGY_PUBLISHED": "publicado",
    "EVIDENCE_PACKAGE_CREATED": "blockchain",
    "ANCHORED": "ancorado",
    "ANCHORING_SIMULATED": "blockchain",
    "VERIFIED": "verificado",
    "VERIFICATION_FAILED": "erro",
    "VALID": "verificado",
    "WARNING": "aguardando-aprovacao",
    "ERROR": "erro",
    "APPROVED": "aprovado",
    "REJECTED": "erro",
    "CORRECTION_REQUESTED": "aguardando-aprovacao",
    "integro": "verificado",
    "divergente": "divergente",
    "PENDING": "pendente",
    "RUNNING": "em-execucao",
    "DONE": "concluido",
    "DONE_WARNINGS": "aguardando-aprovacao",
    "DIVERGENT": "divergente",
}

# Retrocompatibilidade com imports existentes
STATUS_COLORS = STATUS_VARIANTS

EMISSION_SOURCES = [
    "Fermentação entérica — CH₄",
    "Manejo de dejetos — CH₄",
    "Fertilizantes — N₂O",
    "Energia — CO₂",
    "Total GEE — CO₂e",
]

NORMALIZED_STATUSES = [
    "VALID",
    "WARNING",
    "ERROR",
    "IGNORED",
    "CORRECTED",
    "READY_FOR_CANONICAL_MODEL",
]

# Mapeamento de ícones Bootstrap color → classe CSS de wrap
ICON_COLOR_MAP = {
    "success": "green",
    "primary": "petrol",
    "info": "blue",
    "warning": "amber",
    "danger": "red",
    "secondary": "slate",
}

# Ícones inválidos/inexistentes no FA5 free → substitutos
KPI_ICON_ALIASES = {
    "fa-cow": "fa-paw",
    "fa-glass-whiskey": "fa-tint",
}


def resolve_kpi_icon(icon: str) -> str:
    """Normaliza classes Font Awesome para ícones válidos."""
    for old, new in KPI_ICON_ALIASES.items():
        if old in icon:
            icon = icon.replace(old, new)
    return icon
