"""Harmonização declarativa aplicada via normalizers.library."""

from __future__ import annotations

from pathlib import Path

from wrappers.normalizers.harmonization import apply_layout_harmonization, strip_whitespace_strings


def test_strip_whitespace_strings_targeted_fields() -> None:
    rec = {"property_id": "  P1  ", "milk_production": "10"}
    out = strip_whitespace_strings(rec, ["property_id"])
    assert out["property_id"] == "P1"
    assert out["milk_production"] == "10"


def test_strip_whitespace_strings_all_str_when_fields_omitted() -> None:
    rec = {"a": " x ", "_internal": " y ", "n": 1}
    out = strip_whitespace_strings(rec, None)
    assert out["a"] == "x"
    assert out["_internal"] == " y "


def test_apply_layout_harmonization_applies_monthly_layout_strip() -> None:
    from wrappers.registry.file_registry import default_registry

    doc = default_registry().get("monthly:v1")
    rec = {"property_id": "  Fazenda  ", "period_start": "2021-01-01", "_x": 1}
    out = apply_layout_harmonization(doc, rec)
    assert out["property_id"] == "Fazenda"
