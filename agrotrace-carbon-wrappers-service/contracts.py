"""Contratos da camada de wrappers — EcoFarm OS."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class ProcessingStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"


class ErrorCode(str, Enum):
    STRUCTURAL_PARSE_ERROR = "structural_parse_error"
    VALIDATION_ERROR = "validation_error"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    TYPE_ERROR = "type_error"
    DOMAIN_VIOLATION = "domain_violation"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


@dataclass
class ValidationIssue:
    code: ErrorCode | str
    message: str
    severity: Severity
    field: str | None = None
    line_index: int | None = None
    value: Any = None


@dataclass
class ValidationReport:
    rejected_count: int = 0
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)
    rejected_indices: list[int] = field(default_factory=list)

    def add_error(self, issue: ValidationIssue, line_index: int | None = None) -> None:
        self.errors.append(issue)
        if line_index is not None and line_index not in self.rejected_indices:
            self.rejected_indices.append(line_index)
        self.rejected_count = len(self.rejected_indices)

    def add_warning(self, issue: ValidationIssue) -> None:
        self.warnings.append(issue)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rejected_count": self.rejected_count,
            "errors": [
                {
                    "code": e.code.value if isinstance(e.code, ErrorCode) else e.code,
                    "message": e.message,
                    "severity": e.severity.value,
                    "field": e.field,
                    "line_index": e.line_index,
                    "value": e.value,
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "code": w.code.value if isinstance(w.code, ErrorCode) else w.code,
                    "message": w.message,
                    "severity": w.severity.value,
                    "field": w.field,
                    "line_index": w.line_index,
                }
                for w in self.warnings
            ],
            "rejected_indices": self.rejected_indices,
        }


@dataclass
class ProvenanceMetadata:
    source_uri: str
    source_type: str = "csv"
    read_timestamp: str = field(
        default_factory=lambda: datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    )
    checksum: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "source_uri": self.source_uri,
            "source_type": self.source_type,
            "read_timestamp": self.read_timestamp,
        }
        if self.checksum is not None:
            d["checksum"] = self.checksum
        return d


@dataclass
class TemporalDescriptor:
    type: str
    value: str | None = None
    start: str | None = None
    end: str | None = None
    granularity: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.type}
        if self.value is not None:
            d["value"] = self.value
        if self.start is not None:
            d["start"] = self.start
        if self.end is not None:
            d["end"] = self.end
        if self.granularity is not None:
            d["granularity"] = self.granularity
        return d


@dataclass
class OrganizationalDescriptor:
    """Contexto organizacional do registo ou do lote (propriedade, animal, etc.)."""

    granularity: str
    identifier: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"granularity": self.granularity}
        if self.identifier is not None:
            d["identifier"] = self.identifier
        return d


@dataclass
class ProcessingContext:
    """Parâmetros de execução do pipeline (a URI continua no argumento `source_uri` de `process_file`)."""

    encoding: str | None = None
    compute_checksum: bool = False
    year: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def merged_options(self) -> dict[str, Any]:
        """Opções passadas ao pipeline interno; chaves em `extra` podem sobrescrever defaults."""
        out: dict[str, Any] = {}
        if self.encoding is not None:
            out["encoding"] = self.encoding
        out["compute_checksum"] = self.compute_checksum
        if self.year is not None:
            out["year"] = self.year
        out.update(self.extra)
        return out


@dataclass
class SourceContext:
    source_uri: str
    media_type: str | None = "text/csv"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"source_uri": self.source_uri}
        if self.media_type is not None:
            d["media_type"] = self.media_type
        if self.extra:
            d["extra"] = self.extra
        return d


@dataclass
class ProcessingResult:
    layout_id: str
    layout_version: str
    processing_status: ProcessingStatus
    source_context: SourceContext
    normalized_payload: list[dict[str, Any]]
    metadata: dict[str, Any]
    provenance: ProvenanceMetadata
    temporal_context: TemporalDescriptor | dict[str, Any]
    organizational_context: OrganizationalDescriptor | dict[str, Any]
    validation_report: ValidationReport
    quality_flags: list[str]
    source_schema_version: str
    canonical_projection: dict[str, Any] = field(default_factory=dict)
    rejected_records: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        tc = self.temporal_context
        oc = self.organizational_context
        meta = dict(self.metadata)
        if "layout_family" not in meta and meta.get("wrapper_id"):
            meta["layout_family"] = meta["wrapper_id"]
        return {
            "layout_id": self.layout_id,
            "layout_version": self.layout_version,
            "processing_status": self.processing_status.value,
            "source_context": self.source_context.to_dict(),
            "metadata": meta,
            "provenance": self.provenance.to_dict(),
            "normalized_payload": self.normalized_payload,
            "rejected_records": self.rejected_records,
            "temporal_context": tc.to_dict() if hasattr(tc, "to_dict") else tc,
            "organizational_context": oc.to_dict() if hasattr(oc, "to_dict") else oc,
            "validation_report": self.validation_report.to_dict(),
            "quality_flags": self.quality_flags,
            "source_schema_version": self.source_schema_version,
            "canonical_projection": self.canonical_projection,
        }
