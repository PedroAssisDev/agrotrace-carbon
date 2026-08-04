"""Contrato da API pública do módulo wrappers."""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pytest

import wrappers
from wrappers import process_file, process_file_auto
from wrappers.contracts import ProcessingStatus


def test_public_all_exports_core_symbols() -> None:
  expected = {
      "process_file",
      "process_file_auto",
      "LayoutPipeline",
      "ProcessingResult",
      "ExportConfiguration",
      "persist_processing_result",
      "LayoutRegistry",
      "detect_layout_id",
  }
  assert expected <= set(wrappers.__all__)


def test_process_file_metadata_layout_family(tmp_path: Path) -> None:
    p = tmp_path / "in.csv"
    p.write_text("Date,Tag,Milk,Weight\n2021-01-01,A1,10.5,500\n", encoding="utf-8")
    r = process_file(str(p), "intraday:v1")
    assert r.metadata.get("layout_family") == "intraday"
    assert r.metadata.get("wrapper_id") == "intraday"  # compat temporária
    d = r.to_dict()
    assert d["metadata"]["layout_family"] == "intraday"


def test_to_dict_backfills_layout_family_from_wrapper_id() -> None:
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
        metadata={"wrapper_id": "monthly"},
        provenance=ProvenanceMetadata(source_uri="file:///x.csv"),
        temporal_context=TemporalDescriptor(type="interval", granularity="month"),
        organizational_context=OrganizationalDescriptor(granularity="property"),
        validation_report=ValidationReport(),
        quality_flags=[],
        source_schema_version="sha256:abc",
    )
    assert r.to_dict()["metadata"]["layout_family"] == "monthly"


def test_process_file_auto_emits_deprecation_warning(tmp_path: Path) -> None:
    p = tmp_path / "in.csv"
    p.write_text("Date,Tag,Milk,Weight\n2021-01-01,A1,10.5,500\n", encoding="utf-8")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        r = process_file_auto(str(p))
    assert r.processing_status == ProcessingStatus.SUCCESS
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)
