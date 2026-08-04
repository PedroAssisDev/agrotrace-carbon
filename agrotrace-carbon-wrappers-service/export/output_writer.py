"""
OutputWriter — orquestra paths, manifest e artefatos sem acoplar o pipeline interno.

- `processed/`: linhas aceites (normalizado, canónico opcional).
- `rejected/`: linhas rejeitadas (parcial ou falha total com snapshots).
- `validation_reports/`: JSON de validação + manifest de rastreabilidade.
- `logs/`: resumo opcional por execução.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..contracts import ProcessingResult, ValidationReport
from .delimited import DelimitedSerializer
from .export_config import ExportConfiguration


@dataclass(frozen=True)
class ProcessedFileDescriptor:
    path: Path
    kind: str
    layout_id: str
    processing_status: str
    run_id: str


@dataclass(frozen=True)
class RejectedFileDescriptor:
    path: Path
    layout_id: str
    run_id: str
    reason_summary: str


def _write_validation_report(report: ValidationReport, path: Path, encoding: str = "utf-8") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding=encoding)
    return path


def _parse_layout_id(layout_id: str) -> tuple[str, str]:
    if ":" in layout_id:
        fam, ver = layout_id.split(":", 1)
        return fam, ver.replace(".", "_")
    return layout_id, "v1"


def _export_dir(cfg: ExportConfiguration, layout_id: str, *, rejected: bool) -> Path:
    family, version = _parse_layout_id(layout_id)
    root = cfg.rejected_root() if rejected else cfg.processed_root()
    now = datetime.now(UTC)
    parts = [root, family, version]
    if cfg.use_date_subfolders:
        parts.extend([f"{now.year:04d}", f"{now.month:02d}", f"{now.day:02d}"])
    d = Path(*parts)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _ts_compact() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _ensure_data_tree(cfg: ExportConfiguration) -> None:
    if not cfg.ensure_data_layout:
        return
    cfg.input_root().mkdir(parents=True, exist_ok=True)
    cfg.processed_root().mkdir(parents=True, exist_ok=True)
    cfg.rejected_root().mkdir(parents=True, exist_ok=True)
    cfg.logs_root().mkdir(parents=True, exist_ok=True)
    cfg.validation_reports_root().mkdir(parents=True, exist_ok=True)


class OutputWriter:
    def __init__(self, config: ExportConfiguration):
        self.config = config
        self._serializer = DelimitedSerializer(field_separator=config.field_separator)

    def write_all(self, result: ProcessingResult) -> list[ProcessedFileDescriptor | RejectedFileDescriptor]:
        _ensure_data_tree(self.config)

        run_id = str(uuid.uuid4())
        status = result.processing_status.value
        family, version = _parse_layout_id(result.layout_id)
        ts = _ts_compact()
        stem = f"{family}_{version}_{ts}_{status}"

        descriptors: list[ProcessedFileDescriptor | RejectedFileDescriptor] = []
        paths_manifest: dict[str, str] = {}

        enc = self.config.encoding
        out_processed = _export_dir(self.config, result.layout_id, rejected=False)
        out_rejected = _export_dir(self.config, result.layout_id, rejected=True)

        if self.config.write_validation_report:
            vr_path = self.config.validation_reports_root() / f"{run_id}_validation.json"
            _write_validation_report(result.validation_report, vr_path, encoding=enc)
            paths_manifest["validation_report"] = str(vr_path.resolve())
            descriptors.append(
                ProcessedFileDescriptor(vr_path, "validation_report", result.layout_id, status, run_id)
            )

        norm_path: Path | None = None
        if self.config.write_normalized and (
            result.normalized_payload or self.config.write_empty_normalized_on_failure
        ):
            norm_path = out_processed / f"{stem}_normalized{self.config.file_extension}"
            body = self._serializer.write_table(result.normalized_payload)
            norm_path.write_text(body, encoding=enc)
            paths_manifest["output_normalized"] = str(norm_path.resolve())
            descriptors.append(
                ProcessedFileDescriptor(norm_path, "normalized", result.layout_id, status, run_id)
            )

        if self.config.write_canonical and result.canonical_projection:
            proj = result.canonical_projection.get("projections")
            if isinstance(proj, list) and proj:
                can_path = out_processed / f"{stem}_canonical{self.config.file_extension}"
                can_path.write_text(self._serializer.write_table(proj), encoding=enc)
                paths_manifest["output_canonical"] = str(can_path.resolve())
                descriptors.append(
                    ProcessedFileDescriptor(can_path, "canonical", result.layout_id, status, run_id)
                )

        rej_path: Path | None = None
        if self.config.write_rejected and result.rejected_records:
            rej_path = out_rejected / f"{stem}_rejected{self.config.file_extension}"
            rej_path.write_text(self._serializer.write_table(result.rejected_records), encoding=enc)
            paths_manifest["output_rejected"] = str(rej_path.resolve())
            descriptors.append(
                RejectedFileDescriptor(
                    rej_path,
                    result.layout_id,
                    run_id,
                    reason_summary="rejected_rows_export",
                )
            )

        need_stub = (
            result.processing_status.value == "failure"
            and not result.normalized_payload
            and rej_path is None
            and not self.config.write_empty_normalized_on_failure
        )
        if need_stub:
            stub = out_rejected / f"{stem}_no_rows{self.config.file_extension}"
            stub.write_text(self._serializer.write_table([]), encoding=enc)
            paths_manifest["output_rejected_stub"] = str(stub.resolve())
            descriptors.append(
                RejectedFileDescriptor(
                    stub,
                    result.layout_id,
                    run_id,
                    reason_summary="failure_without_rows_or_rejected_export",
                )
            )

        if self.config.write_processing_log:
            log_path = self.config.logs_root() / f"{run_id}_processing.json"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                json.dumps(
                    {
                        "run_id": run_id,
                        "layout_id": result.layout_id,
                        "status": status,
                        "record_count": len(result.normalized_payload),
                        "rejected_record_count": len(result.rejected_records),
                        "source_uri": result.source_context.source_uri,
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding=enc,
            )
            paths_manifest["processing_log"] = str(log_path.resolve())

        if self.config.write_manifest:
            man_path = self.config.validation_reports_root() / f"{run_id}_manifest.json"
            man_path.parent.mkdir(parents=True, exist_ok=True)
            paths_with_manifest = {
                **paths_manifest,
                "manifest": str(man_path.resolve()),
            }
            src_uri = result.source_context.source_uri
            src_path = src_uri.replace("file://", "").lstrip("/")
            try:
                input_basename = Path(src_path).name
            except Exception:
                input_basename = src_uri
            manifest = {
                "run_id": run_id,
                "layout_id": result.layout_id,
                "layout_family": family,
                "layout_catalog_version": version,
                "layout_version": result.layout_version,
                "catalog_display_name": result.metadata.get("catalog_display_name"),
                "processing_status": status,
                "processing_timestamp_utc": result.metadata.get("processing_timestamp"),
                "source_uri": src_uri,
                "source_input_basename": input_basename,
                "source_checksum_sha256": result.provenance.checksum,
                "field_separator": self.config.field_separator,
                "encoding": enc,
                "quality_flags": result.quality_flags,
                "source_schema_version": result.source_schema_version,
                "rejected_record_count": len(result.rejected_records),
                "accepted_record_count": len(result.normalized_payload),
                "paths": paths_with_manifest,
            }
            man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding=enc)
            descriptors.append(
                ProcessedFileDescriptor(man_path, "manifest", result.layout_id, status, run_id)
            )

        return descriptors


def persist_processing_result(result: ProcessingResult, config: ExportConfiguration) -> list[Any]:
    """API única pós-pipeline: persiste artefatos conforme config."""
    return OutputWriter(config).write_all(result)
