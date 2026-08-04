"""Exportacao pos-wrapper (delimitador ;_;)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wrappers.export import ExportConfiguration, persist_processing_result
from wrappers.export.delimited import DelimitedSerializer
from wrappers.export.output_writer import OutputWriter


def test_delimited_roundtrip_multichar_separator() -> None:
    sep = ";_;"
    s = DelimitedSerializer(field_separator=sep)
    rows = [{"a": "1", "b": f"x{sep}y"}, {"a": "2", "b": "ok"}]
    text = s.write_table(rows, columns=["a", "b"])
    assert sep in text
    lines = text.strip().split("\n")
    assert lines[0] == f"a{sep}b"
    # valor com separador literal deve ser citado para não partir colunas
    assert lines[1] == f'1{sep}"x{sep}y"'
    assert lines[2] == f"2{sep}ok"


def test_persist_writes_manifest_and_normalized(tmp_path: Path) -> None:
    from wrappers.contracts import (
        OrganizationalDescriptor,
        ProcessingResult,
        ProcessingStatus,
        ProvenanceMetadata,
        SourceContext,
        TemporalDescriptor,
        ValidationReport,
    )

    result = ProcessingResult(
        layout_id="intraday:v1",
        layout_version="1.0",
        processing_status=ProcessingStatus.SUCCESS,
        source_context=SourceContext(source_uri="file:///in.csv"),
        normalized_payload=[{"date": "2021-01-01", "animal_id": "1", "milk": 1.0, "weight": 500.0}],
        metadata={"processing_timestamp": "2025-01-01T00:00:00Z"},
        provenance=ProvenanceMetadata(source_uri="in.csv"),
        temporal_context=TemporalDescriptor(type="instant", granularity="day"),
        organizational_context=OrganizationalDescriptor(granularity="animal"),
        validation_report=ValidationReport(),
        quality_flags=[],
        source_schema_version="test",
        canonical_projection={"projections": [{"Animal.identifier": "1"}]},
    )
    cfg = ExportConfiguration(base_dir=tmp_path, use_date_subfolders=False)
    desc = persist_processing_result(result, cfg)
    assert desc
    manifests = list((tmp_path / "validation_reports").glob("*_manifest.json"))
    assert manifests
    man = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert man["field_separator"] == ";_;"
    assert man.get("source_input_basename") == "in.csv"
    assert man.get("layout_family") == "intraday"
    assert "output_normalized" in man["paths"]


def test_export_writes_rejected_sidecar(tmp_path: Path) -> None:
    from wrappers.contracts import (
        OrganizationalDescriptor,
        ProcessingResult,
        ProcessingStatus,
        ProvenanceMetadata,
        SourceContext,
        TemporalDescriptor,
        ValidationReport,
    )

    result = ProcessingResult(
        layout_id="intraday:v1",
        layout_version="1.0",
        processing_status=ProcessingStatus.PARTIAL_SUCCESS,
        source_context=SourceContext(source_uri="file:///in.csv"),
        normalized_payload=[{"date": "2021-01-01", "animal_id": "1", "milk": 1.0, "weight": 500.0}],
        metadata={"processing_timestamp": "2025-01-01T00:00:00Z"},
        provenance=ProvenanceMetadata(source_uri="in.csv"),
        temporal_context=TemporalDescriptor(type="instant", granularity="day"),
        organizational_context=OrganizationalDescriptor(granularity="animal"),
        validation_report=ValidationReport(),
        quality_flags=["validation_warnings"],
        source_schema_version="test",
        canonical_projection={},
        rejected_records=[
            {"date": "2021-01-02", "animal_id": "2", "milk": -1, "weight": 400, "_line_index": 1, "_reject_phase": "validation"}
        ],
    )
    cfg = ExportConfiguration(base_dir=tmp_path, use_date_subfolders=False)
    OutputWriter(cfg).write_all(result)
    rejected_files = list(tmp_path.glob("rejected/**/*_rejected*"))
    assert rejected_files
    man = json.loads(list((tmp_path / "validation_reports").glob("*_manifest.json"))[0].read_text(encoding="utf-8"))
    assert man.get("rejected_record_count") == 1
    assert "output_rejected" in man["paths"]


def test_ensure_data_layout_creates_input_and_logs(tmp_path: Path) -> None:
    cfg = ExportConfiguration(base_dir=tmp_path, use_date_subfolders=False, write_processing_log=True)
    from wrappers.contracts import (
        OrganizationalDescriptor,
        ProcessingResult,
        ProcessingStatus,
        ProvenanceMetadata,
        SourceContext,
        TemporalDescriptor,
        ValidationReport,
    )

    r = ProcessingResult(
        layout_id="monthly:v1",
        layout_version="1.0",
        processing_status=ProcessingStatus.SUCCESS,
        source_context=SourceContext(source_uri="file:///x.csv"),
        normalized_payload=[],
        metadata={"processing_timestamp": "2025-01-01T00:00:00Z"},
        provenance=ProvenanceMetadata(source_uri="x.csv"),
        temporal_context=TemporalDescriptor(type="interval", granularity="month"),
        organizational_context=OrganizationalDescriptor(granularity="property"),
        validation_report=ValidationReport(),
        quality_flags=[],
        source_schema_version="t",
        canonical_projection={},
    )
    persist_processing_result(r, cfg)
    assert (tmp_path / "input").is_dir()
    assert (tmp_path / "logs").is_dir()
    assert list((tmp_path / "logs").glob("*.json"))
