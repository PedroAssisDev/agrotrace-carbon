"""Regressão: str.Enum não deve cair no default monthly via str(enum)."""

from __future__ import annotations

from services.domain_catalog import (
    TemporalGranularity,
    normalize_temporal,
    temporal_to_calc_scope,
)


def test_normalize_temporal_accepts_enum_member():
    assert normalize_temporal(TemporalGranularity.ANNUAL) is TemporalGranularity.ANNUAL
    assert normalize_temporal(TemporalGranularity.MONTHLY) is TemporalGranularity.MONTHLY


def test_temporal_to_calc_scope_annual_string_and_enum():
    assert temporal_to_calc_scope("annual") == "annual"
    assert temporal_to_calc_scope(TemporalGranularity.ANNUAL) == "annual"


def test_unknown_temporal_label_does_not_map_to_annual():
    unknown = "year" + "ly"  # rótulo legado não aceito como canônico
    assert normalize_temporal(unknown) is not TemporalGranularity.ANNUAL
    assert temporal_to_calc_scope(unknown) != "annual"


def test_adapter_chain_normalize_then_to_calc_scope():
    """Cadeia usada em calculation_adapter._infer_temporal_scope_key."""
    assert temporal_to_calc_scope(normalize_temporal("annual")) == "annual"
    assert temporal_to_calc_scope(normalize_temporal(str("annual"))) == "annual"
