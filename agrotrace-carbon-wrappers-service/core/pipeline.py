"""
Pipeline principal — ingestão orientada a layout (registry + engines).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..contracts import (
    OrganizationalDescriptor,
    ProcessingContext,
    ProcessingResult,
    ProcessingStatus,
    ProvenanceMetadata,
    SourceContext,
    TemporalDescriptor,
    ValidationReport,
)
from ..core.row_snapshot import logical_row_snapshot
from ..mappers.engine import CanonicalMappingEngine
from ..normalizers.engine import NormalizationEngine
from ..core.field_mapping import map_raw_row_to_logical
from ..normalizers.harmonization import apply_layout_harmonization
from ..processors.csv_processor import read_csv_rows
from ..provenance import build_provenance
from ..registry.file_registry import LayoutRegistry, default_registry
from ..temporal import date_to_iso, parse_date
from ..validators.engine import ValidationEngine

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[misc, assignment]

logger = logging.getLogger(__name__)


def _load_numeric_fields(layout_dir: Path, filename: str) -> frozenset[str]:
    if yaml is None:
        return frozenset()
    try:
        p = layout_dir / filename
        with open(p, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, list):
            return frozenset(str(x) for x in data)
    except Exception as e:
        logger.warning("Falha ao carregar numeric_fields: %s", e)
    return frozenset()


class LayoutPipeline:
    """
    Executa o fluxo: leitura física → mapeamento lógico → validação → normalização
    → harmonização semântica (extensível) → projeção canônica.
    """

    def __init__(
        self,
        layout_doc: dict[str, Any],
        *,
        layout_dir: Path,
        registry: LayoutRegistry | None = None,
    ):
        self.doc = layout_doc
        self.layout_dir = layout_dir
        self.layout_id = str(layout_doc["layout_id"])
        self.layout_version = str(layout_doc.get("version", "1.0"))
        self.layout_family = str(layout_doc.get("layout_family", ""))
        self.registry = registry
        schema = layout_doc.get("schema") or {}
        self._numeric_annual: frozenset[str] = frozenset()
        if schema.get("mode") == "snake_case_headers":
            nf = schema.get("numeric_fields_file")
            if nf:
                self._numeric_annual = _load_numeric_fields(layout_dir, nf)
        self._validation = ValidationEngine()
        self._mapper = CanonicalMappingEngine()
        self._normalizer = NormalizationEngine(self.doc, numeric_annual=self._numeric_annual)
        self._validation_rules = self._resolve_validation_rules(
            layout_doc.get("validation_rules") or []
        )

    def _resolve_validation_rules(self, rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for r in rules:
            if r.get("ref") == "annual_numeric_non_negative" and r.get("__dynamic__"):
                out.append(
                    {
                        "ref": "annual_numeric_non_negative",
                        "fields": sorted(self._numeric_annual),
                    }
                )
            else:
                out.append(dict(r))
        return out

    @classmethod
    def from_layout_id(cls, layout_id: str, registry: LayoutRegistry | None = None) -> LayoutPipeline:
        reg = registry or default_registry()
        doc = reg.get(layout_id)
        return cls(doc, layout_dir=reg.layout_directory(layout_id), registry=reg)

    def process_file(
        self,
        source_uri: str,
        *,
        encoding: str | None = None,
        compute_checksum: bool = False,
        **options: Any,
    ) -> ProcessingResult:
        options = dict(options)
        options["source_uri"] = source_uri
        read_ts = datetime.now(UTC)
        file_path = Path(source_uri.replace("file://", "").lstrip("/"))

        provenance = build_provenance(
            source_uri=source_uri,
            source_type=self.doc.get("physical", {}).get("format", "csv"),
            read_timestamp=read_ts,
            compute_checksum=compute_checksum,
            file_path=file_path if file_path.exists() else None,
        )

        physical = self.doc.get("physical") or {}
        delim = physical.get("delimiter", ",")
        enc = encoding or physical.get("encoding", "utf-8")

        report = ValidationReport()
        payload: list[dict[str, Any]] = []
        rejected_records: list[dict[str, Any]] = []
        quality_flags: list[str] = []

        try:
            raw_rows = read_csv_rows(source_uri, delimiter=delim, encoding=enc)
        except Exception as e:
            logger.exception("Falha na leitura: %s", e)
            from ..contracts import ErrorCode, Severity, ValidationIssue

            report.add_error(
                ValidationIssue(
                    code=ErrorCode.STRUCTURAL_PARSE_ERROR,
                    message=str(e),
                    severity=Severity.ERROR,
                    field=None,
                    line_index=None,
                )
            )
            return self._build_result(
                [],
                report,
                provenance,
                quality_flags + ["parse_failure"],
                ProcessingStatus.FAILURE,
                source_uri,
                options,
                rejected_records=rejected_records,
            )

        projections = (self.doc.get("canonical_mapping") or {}).get("projections") or []

        for line_index, raw in enumerate(raw_rows):
            if not raw or all(v is None or (isinstance(v, str) and not v.strip()) for v in raw.values()):
                continue

            row = self._map_logical_row(raw)
            self._inject_parsed_dates(row)

            ok = self._validation.apply(
                self._validation_rules,
                row,
                line_index,
                report,
            )
            if not ok:
                snap = logical_row_snapshot(row)
                snap["_line_index"] = line_index
                snap["_reject_phase"] = "validation"
                rejected_records.append(snap)
                continue

            finalized = self._normalizer.finalize_record(row, line_index, report, options)
            if finalized is None:
                snap = logical_row_snapshot(row)
                snap["_line_index"] = line_index
                snap["_reject_phase"] = "normalization"
                rejected_records.append(snap)
                continue
            harmonized = apply_layout_harmonization(self.doc, finalized)
            payload.append(harmonized)

        status = ProcessingStatus.SUCCESS
        if report.rejected_count > 0 and payload:
            status = ProcessingStatus.PARTIAL_SUCCESS
            quality_flags.append("validation_warnings")
        elif report.rejected_count > 0 and not payload:
            status = ProcessingStatus.FAILURE
            quality_flags.append("all_records_rejected")
        if report.warnings:
            quality_flags.append("validation_warnings")

        stripped = [{k: v for k, v in r.items() if not k.startswith("_")} for r in payload]
        canonical = self._mapper.project_batch(
            stripped,
            projections,
            layout_family=self.layout_family,
            layout_id=self.layout_id,
        )

        return self._build_result(
            payload,
            report,
            provenance,
            quality_flags,
            status,
            source_uri,
            options,
            canonical_projection=canonical,
            rejected_records=rejected_records,
        )

    def _map_logical_row(self, raw: dict[str, Any]) -> dict[str, Any]:
        schema = self.doc.get("schema") or {}
        return map_raw_row_to_logical(raw, schema)

    def _inject_parsed_dates(self, row: dict[str, Any]) -> None:
        schema = self.doc.get("schema") or {}
        fields = schema.get("fields") or []
        for spec in fields:
            if spec.get("type") == "date":
                logical = spec["logical"]
                d = parse_date(row.get(logical))
                if d is not None:
                    row["_parsed_date"] = d
                    row[logical] = date_to_iso(d)
                break

    def _build_result(
        self,
        payload: list[dict[str, Any]],
        report: ValidationReport,
        provenance: ProvenanceMetadata,
        quality_flags: list[str],
        status: ProcessingStatus,
        source_uri: str,
        options: dict[str, Any],
        canonical_projection: dict[str, Any] | None = None,
        *,
        rejected_records: list[dict[str, Any]] | None = None,
    ) -> ProcessingResult:
        reg = self.registry or default_registry()
        try:
            schema_fp = reg.source_schema_fingerprint(self.layout_id)
        except Exception:
            schema_fp = f"{self.layout_id}@embedded"

        gran = self.doc.get("granularity") or {}
        temporal = gran.get("temporal", "instant")
        org = gran.get("organizational", "property")

        td: TemporalDescriptor
        if temporal == "instant":
            td = TemporalDescriptor(type="instant", granularity="day")
        elif temporal == "interval_month":
            td = TemporalDescriptor(type="interval", granularity="month")
        elif temporal == "interval_year":
            td = TemporalDescriptor(type="interval", granularity="year")
        else:
            td = TemporalDescriptor(type="instant", granularity="day")

        oc = OrganizationalDescriptor(granularity=org)

        rej = list(rejected_records or [])
        catalog_name = self.doc.get("catalog_display_name")
        meta = {
            "layout_family": self.layout_family,
            "wrapper_id": self.layout_family,  # compat: removido em versão futura
            "layout_id": self.layout_id,
            "catalog_display_name": str(catalog_name).strip() if catalog_name else None,
            "processing_timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S") + "Z",
            "record_count": len(payload),
            "rejected_record_count": len(rej),
            "status": status.value,
        }

        return ProcessingResult(
            layout_id=self.layout_id,
            layout_version=self.layout_version,
            processing_status=status,
            source_context=SourceContext(source_uri=source_uri, media_type="text/csv", extra={k: v for k, v in options.items() if k != "source_uri"}),
            normalized_payload=payload,
            metadata=meta,
            provenance=provenance,
            temporal_context=td,
            organizational_context=oc,
            validation_report=report,
            quality_flags=quality_flags,
            source_schema_version=schema_fp,
            canonical_projection=canonical_projection or {},
            rejected_records=rej,
        )


def process_file(
    source_uri: str,
    layout_id: str,
    *,
    registry: LayoutRegistry | None = None,
    processing_context: ProcessingContext | None = None,
    **options: Any,
) -> ProcessingResult:
    """Ponto de entrada: processa arquivo com layout explícito (recomendado para MVP).

    Opcional: ``export_config=ExportConfiguration(base_dir=Path(...))`` persiste saida
    pos-wrapper (delimitador ;_;, manifest, validation_report) sem acoplar o nucleo.

    ``processing_context`` agrega encoding, ano, checksum e opções extra sem colidir com a URI.
    """
    opts = dict(options)
    export_cfg = opts.pop("export_config", None)
    if processing_context is not None:
        ctx_opts = processing_context.merged_options()
        for k, v in ctx_opts.items():
            opts.setdefault(k, v)
    pipe = LayoutPipeline.from_layout_id(layout_id, registry=registry)
    result = pipe.process_file(source_uri, **opts)
    if export_cfg is not None:
        from ..export import persist_processing_result

        persist_processing_result(result, export_cfg)
    return result


