"""Evolução: leitura ;_;, deteção de layout, governança de manifest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wrappers.core.pipeline import process_file_auto
from wrappers.export.delimited import DelimitedSerializer
from wrappers.export.delimited_reader import read_delimited_table
from wrappers.export.manifest import validate_export_manifest
from wrappers.registry.layout_detector import LayoutDetectionError, detect_layout_id
from wrappers.registry.file_registry import default_registry


def test_read_delimited_roundtrip_with_writer() -> None:
    sep = ";_;"
    # JSON com chaves entre aspas contém `"`; o escrito citará o campo. Lista `[1]` evita ambiguidade no leitor.
    rows = [
        {"a": "1", "b": f"x{sep}y"},
        {"a": "2", "b": "ok", "nested": [1]},
    ]
    text = DelimitedSerializer(field_separator=sep).write_table(rows, columns=["a", "b", "nested"])
    cols, back = read_delimited_table(text, field_separator=sep)
    assert cols == ["a", "b", "nested"]
    assert back[0]["a"] == "1"
    assert back[0]["b"] == f"x{sep}y"
    assert back[1]["nested"] == [1]


def test_detect_layout_intraday(tmp_path: Path) -> None:
    p = tmp_path / "x.csv"
    p.write_text("Date,Tag,Milk,Weight\n2021-01-01,A1,1,500\n", encoding="utf-8")
    assert detect_layout_id(p, registry=default_registry()) == "intraday:v1"


def test_detect_layout_monthly(tmp_path: Path) -> None:
    p = tmp_path / "m.csv"
    p.write_text(
        "Property;Period;Milk_Production;Milk_Sales\nP1;2021-01-01;10;1\n",
        encoding="utf-8",
    )
    assert detect_layout_id(p, registry=default_registry()) == "monthly:v1"


def test_detect_layout_annual_min_columns(tmp_path: Path) -> None:
    p = tmp_path / "a.csv"
    cols = ["Property_Name"] + [f"Extra_{i}" for i in range(20)]
    header = ";".join(cols)
    p.write_text(header + "\n", encoding="utf-8")
    assert detect_layout_id(p, registry=default_registry()) == "annual:v1"


def test_process_file_auto_intraday(tmp_path: Path) -> None:
    p = tmp_path / "x.csv"
    p.write_text("Date,Tag,Milk,Weight\n2021-01-01,A1,10.5,500\n", encoding="utf-8")
    r = process_file_auto(str(p))
    assert r.layout_id == "intraday:v1"
    assert len(r.normalized_payload) == 1


def test_detect_layout_raises_ambiguous(tmp_path: Path) -> None:
    p = tmp_path / "bad.csv"
    p.write_text("only_one_column\n", encoding="utf-8")
    assert detect_layout_id(p, registry=default_registry()) is None


def test_process_file_auto_raises_layout_detection_error(tmp_path: Path) -> None:
    p = tmp_path / "bad.csv"
    p.write_text("only_one_column\n", encoding="utf-8")
    with pytest.raises(LayoutDetectionError) as ei:
        process_file_auto(str(p))
    assert ei.value.source_path


def test_validate_export_manifest_ok_minimal() -> None:
    m = {
        "run_id": "u",
        "layout_id": "intraday:v1",
        "processing_status": "success",
        "source_uri": "file:///x.csv",
        "field_separator": ";_;",
        "encoding": "utf-8",
        "paths": {"manifest": "/tmp/m.json"},
    }
    assert validate_export_manifest(m) == []


def test_validate_export_manifest_missing_keys() -> None:
    errs = validate_export_manifest({"run_id": "x"})
    assert len(errs) >= 1


def test_persist_manifest_passes_governance(tmp_path: Path) -> None:
    from wrappers.contracts import (
        OrganizationalDescriptor,
        ProcessingResult,
        ProcessingStatus,
        ProvenanceMetadata,
        SourceContext,
        TemporalDescriptor,
        ValidationReport,
    )
    from wrappers.export import ExportConfiguration, persist_processing_result

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
        canonical_projection={},
    )
    persist_processing_result(result, ExportConfiguration(base_dir=tmp_path, use_date_subfolders=False))
    man_path = next((tmp_path / "validation_reports").glob("*_manifest.json"))
    man = json.loads(man_path.read_text(encoding="utf-8"))
    assert validate_export_manifest(man) == []
