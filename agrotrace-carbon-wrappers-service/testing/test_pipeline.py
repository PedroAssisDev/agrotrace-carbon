"""Testes de regressão dos layouts V1 (registry + pipeline)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]

from wrappers.core.pipeline import process_file
from wrappers.contracts import ProcessingContext, ProcessingStatus
from wrappers.data_paths import ANNUAL_CSV_NAMES, INTRADAY_CSV_NAMES, MONTHLY_CSV_NAMES, resolve_csv
from wrappers.export import ExportConfiguration
from wrappers.registry.file_registry import default_registry
from wrappers.registry.layout_definition import LayoutDefinition


@pytest.fixture
def data_dir() -> Path:
    d = SERVICE_ROOT / "data"
    if not d.is_dir():
        pytest.skip("data/ não encontrado")
    return d


def test_registry_lists_v1_layouts() -> None:
    ids = default_registry().list_layout_ids()
    assert "intraday:v1" in ids
    assert "monthly:v1" in ids
    assert "annual:v1" in ids


def test_layout_definition_from_registry() -> None:
    reg = default_registry()
    d = reg.get_definition("intraday:v1")
    assert isinstance(d, LayoutDefinition)
    assert d.layout_family == "intraday"
    assert d.version == "1.0"
    assert d.catalog_display_name == "IntradayLayoutV1"


def test_all_v1_catalog_display_names() -> None:
    reg = default_registry()
    assert reg.get_definition("intraday:v1").catalog_display_name == "IntradayLayoutV1"
    assert reg.get_definition("monthly:v1").catalog_display_name == "MonthlyLayoutV1"
    assert reg.get_definition("annual:v1").catalog_display_name == "AnnualLayoutV1"


def test_registry_list_layout_definitions() -> None:
    defs = default_registry().list_definitions()
    ids = {d.layout_id for d in defs}
    assert ids >= {"intraday:v1", "monthly:v1", "annual:v1"}


def test_process_file_with_export_config(tmp_path: Path) -> None:
    p = tmp_path / "in.csv"
    p.write_text("Date,Tag,Milk,Weight\n2021-01-01,A1,10.5,500\n", encoding="utf-8")
    out_base = tmp_path / "data"
    cfg = ExportConfiguration(base_dir=out_base, use_date_subfolders=False)
    r = process_file(str(p), "intraday:v1", export_config=cfg)
    assert r.processing_status == ProcessingStatus.SUCCESS
    manifests = list((out_base / "validation_reports").glob("*_manifest.json"))
    assert manifests
    man = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert man.get("catalog_display_name") == "IntradayLayoutV1"


def test_processing_context_merges_year(tmp_path) -> None:
    p = tmp_path / "annual_one.csv"
    # Valores numéricos devem ser >= 0 (AnnualLayoutV1 + regra annual_numeric_non_negative).
    p.write_text("Property_Name;Lactating_Cows\nFarm;10\n", encoding="utf-8")
    ctx = ProcessingContext(year=2022)
    r = process_file(str(p), "annual:v1", processing_context=ctx)
    assert r.normalized_payload[0].get("year") == 2022


def test_partial_success_collects_rejected_records(tmp_path) -> None:
    """Uma linha válida e uma inválida (leite negativo) → partial + rejected_records."""
    p = tmp_path / "mix.csv"
    p.write_text("Date,Tag,Milk,Weight\n2021-01-01,A1,10.5,500\n2021-01-02,A2,-1,400\n", encoding="utf-8")
    r = process_file(str(p), "intraday:v1")
    assert r.processing_status == ProcessingStatus.PARTIAL_SUCCESS
    assert len(r.normalized_payload) == 1
    assert len(r.rejected_records) == 1
    assert r.rejected_records[0].get("_reject_phase") == "validation"


def test_intraday_v1(data_dir: Path) -> None:
    p = resolve_csv(data_dir, INTRADAY_CSV_NAMES)
    if not p:
        pytest.skip("CSV intradiário ausente")
    r = process_file(str(p), "intraday:v1")
    assert r.processing_status == ProcessingStatus.SUCCESS
    assert len(r.normalized_payload) >= 100
    assert r.normalized_payload[0].get("animal_id")
    assert r.canonical_projection.get("projections")


def test_monthly_v1(data_dir: Path) -> None:
    p = resolve_csv(data_dir, MONTHLY_CSV_NAMES)
    if not p:
        pytest.skip("CSV mensal ausente")
    r = process_file(str(p), "monthly:v1")
    assert r.processing_status == ProcessingStatus.SUCCESS
    assert len(r.normalized_payload) >= 10
    rec = r.normalized_payload[0]
    assert rec.get("property_id")
    assert rec.get("period_end")


def test_annual_v1(data_dir: Path) -> None:
    p = resolve_csv(data_dir, ANNUAL_CSV_NAMES)
    if not p:
        pytest.skip("CSV anual ausente")
    r = process_file(str(p), "annual:v1", year=2022)
    assert r.processing_status == ProcessingStatus.SUCCESS
    assert len(r.normalized_payload) >= 1
    assert r.normalized_payload[0].get("year") == 2022
    assert r.normalized_payload[0].get("property_name")


def test_monthly_layout_harmonization_strip_property_id(tmp_path: Path) -> None:
    p = tmp_path / "monthly.csv"
    p.write_text(
        "Property;Period;Milk_Production;Milk_Sales\n  Fazenda  ;2021-01-01;10;9\n",
        encoding="utf-8",
    )
    r = process_file(str(p), "monthly:v1")
    assert r.processing_status == ProcessingStatus.SUCCESS
    assert r.normalized_payload[0]["property_id"] == "Fazenda"
