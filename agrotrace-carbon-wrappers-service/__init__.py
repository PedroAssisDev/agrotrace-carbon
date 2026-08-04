"""
Camada de wrappers — EcoFarm OS.

API principal
-------------
``process_file(source_uri, layout_id, ...)`` — processamento com layout explícito.
``detect_layout_id`` — inferência de layout pelo cabeçalho (usar com ``process_file``).
``LayoutPipeline`` — orquestrador OO para testes e extensão avançada.
"""

from __future__ import annotations

__version__ = "1.0.0"

import sys

# Pytest importa este ficheiro como ``__init__`` quando ``testing/`` está dentro do pacote.
if not __package__:
    __package__ = "wrappers"
    sys.modules.setdefault("wrappers", sys.modules[__name__])

from .contracts import (
    ErrorCode,
    OrganizationalDescriptor,
    ProcessingContext,
    ProcessingResult,
    ProcessingStatus,
    ProvenanceMetadata,
    Severity,
    SourceContext,
    TemporalDescriptor,
    ValidationIssue,
    ValidationReport,
)
from .core.pipeline import LayoutPipeline, process_file
from .export import ExportConfiguration, persist_processing_result
from .registry import (
    LayoutDefinition,
    LayoutDetectionError,
    LayoutRegistry,
    default_registry,
    detect_layout_id,
)

from .export import DelimitedExportStrategy  # noqa: F401
from .provenance import build_provenance  # noqa: F401
from .temporal import (  # noqa: F401
    date_to_iso,
    interval_for_month,
    interval_for_year,
    parse_date,
    temporal_instant,
    temporal_interval_month,
    temporal_interval_year,
)

__all__ = [
    "process_file",
    "LayoutPipeline",
    "ProcessingResult",
    "ProcessingContext",
    "ProcessingStatus",
    "ExportConfiguration",
    "persist_processing_result",
    "LayoutRegistry",
    "LayoutDefinition",
    "default_registry",
    "detect_layout_id",
    "LayoutDetectionError",
    "ErrorCode",
    "SourceContext",
    "ProvenanceMetadata",
    "TemporalDescriptor",
    "OrganizationalDescriptor",
    "ValidationIssue",
    "ValidationReport",
    "Severity",
]
