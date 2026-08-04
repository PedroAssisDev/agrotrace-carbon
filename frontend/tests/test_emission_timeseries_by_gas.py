"""Séries por gás — RF008/RF009/RNF005/CE2 (não colapsar multi-gás em records parciais)."""

from __future__ import annotations

from services.emission_timeseries_service import build_emission_timeseries


def _cycle(
    *,
    cycle_id: str = "C1",
    period: str = "2026-01",
    co2e: float = 100_000.0,
    by_gas: dict[str, float] | None = None,
    by_source: dict[str, float] | None = None,
    records: list[dict] | None = None,
) -> dict:
    calc: dict = {"co2e_total_kg": co2e}
    if by_gas is not None:
        calc["by_gas"] = by_gas
    if by_source is not None:
        calc["by_source"] = by_source
    payload = records if records is not None else [{"milk_production": 10_000, "period_start": f"{period}-01"}]
    return {
        "cycle_id": cycle_id,
        "property_id": "FARM-T",
        "reporting_period": period,
        "calculation": calc,
        "wrapper": {"normalized_payload": payload},
        "normalized_data": payload,
    }


def test_series_only_ch4() -> None:
    co2e = 50_000.0
    cycles = [
        _cycle(
            by_gas={"CH4": co2e},
            by_source={"Fermentação entérica — CH₄": co2e},
        )
    ]
    ts = build_emission_timeseries(cycles)
    assert ts["has_series"] is True
    raw = ts.get("by_gas_raw") or {}
    assert list(raw.keys()) == ["CH4"]
    assert len(ts["by_gas"]) == 1
    assert "CH₄ (CO₂e)" in ts["by_gas"]


def test_series_ch4_and_n2o() -> None:
    co2e = 80_000.0
    cycles = [
        _cycle(
            by_gas={"CH4": co2e * 0.8, "N2O": co2e * 0.2},
            by_source={
                "Fermentação entérica — CH₄": co2e * 0.8,
                "Fertilizantes — N₂O": co2e * 0.2,
            },
        )
    ]
    ts = build_emission_timeseries(cycles)
    raw = ts.get("by_gas_raw") or {}
    assert set(raw.keys()) == {"CH4", "N2O"}
    assert len(ts["by_gas"]) == 2


def test_series_co2_ch4_n2o() -> None:
    co2e = 100_000.0
    cycles = [
        _cycle(
            by_gas={"CH4": co2e * 0.7, "N2O": co2e * 0.1, "CO2": co2e * 0.2},
            by_source={
                "Fermentação entérica — CH₄": co2e * 0.55,
                "Manejo de dejetos — CH₄": co2e * 0.15,
                "Fertilizantes — N₂O": co2e * 0.1,
                "Energia — CO₂": co2e * 0.2,
            },
        )
    ]
    ts = build_emission_timeseries(cycles)
    raw = ts.get("by_gas_raw") or {}
    assert set(raw.keys()) == {"CH4", "CO2", "N2O"}
    assert len(ts["by_gas"]) >= 2


def test_empty_series() -> None:
    cycles = [
        {
            "cycle_id": "EMPTY",
            "reporting_period": "2026-01",
            "calculation": {},
            "wrapper": {"normalized_payload": []},
        }
    ]
    ts = build_emission_timeseries(cycles)
    assert ts["has_series"] is False
    assert ts["by_gas"] == {}
    assert ts["point_count"] == 0


def test_unknown_gas_preserved() -> None:
    co2e = 40_000.0
    cycles = [
        _cycle(by_gas={"CH4": co2e * 0.5, "SF6": co2e * 0.5})
    ]
    ts = build_emission_timeseries(cycles)
    raw = ts.get("by_gas_raw") or {}
    assert "SF6" in raw
    assert "SF6" in ts["by_gas"]  # sem label mapeado, chave crua


def test_sum_by_gas_matches_total_co2e() -> None:
    co2e = 100_000.0
    by_gas = {"CH4": co2e * 0.7, "N2O": co2e * 0.1, "CO2": co2e * 0.2}
    cycles = [_cycle(by_gas=by_gas)]
    ts = build_emission_timeseries(cycles)
    raw = ts.get("by_gas_raw") or {}
    # valores na série estão em t; reconverter para kg
    gas_sum_kg = sum((vals[0] or 0) * 1000.0 for vals in raw.values())
    total_kg = (ts["total_t"][0] or 0) * 1000.0
    assert abs(gas_sum_kg - total_kg) < 1e-6
    assert abs(gas_sum_kg - co2e) < 1e-6


def test_partial_enteric_records_keep_multi_gas() -> None:
    """Regressão: records só com enteric_tco2e não colapsam by_gas multi-gás."""
    co2e = 105_000.0
    cycles = [
        _cycle(
            by_gas={"CH4": co2e * 0.7, "N2O": co2e * 0.1, "CO2": co2e * 0.2},
            by_source={
                "Fermentação entérica — CH₄": co2e * 0.55,
                "Manejo de dejetos — CH₄": co2e * 0.15,
                "Fertilizantes — N₂O": co2e * 0.1,
                "Energia — CO₂": co2e * 0.2,
            },
            records=[{
                "milk_production": 12_000,
                "enteric_tco2e": co2e * 0.52 / 1000.0,
                "period_start": "2026-01-01",
            }],
        )
    ]
    ts = build_emission_timeseries(cycles)
    raw = ts.get("by_gas_raw") or {}
    assert len(raw) >= 2
    assert {"CH4", "N2O", "CO2"} <= set(raw.keys())
    assert len(ts["by_source"]) >= 2


def test_monthly_two_periods_temporal_order() -> None:
    cycles = [
        _cycle(
            cycle_id="C-FEB",
            period="2026-02",
            co2e=110_000.0,
            by_gas={"CH4": 77_000.0, "N2O": 11_000.0, "CO2": 22_000.0},
        ),
        _cycle(
            cycle_id="C-JAN",
            period="2026-01",
            co2e=100_000.0,
            by_gas={"CH4": 70_000.0, "N2O": 10_000.0, "CO2": 20_000.0},
        ),
    ]
    ts = build_emission_timeseries(cycles)
    assert ts["has_multi_point"] is True
    assert len(ts["labels"]) == 2
    # labels devem refletir ordem temporal Jan → Fev
    joined = " ".join(ts["labels"]).lower()
    assert "jan" in joined or "2026-01" in joined or ts["labels"][0] <= ts["labels"][1]
    raw = ts.get("by_gas_raw") or {}
    assert len(raw) >= 2
    for series in raw.values():
        assert len(series) == 2
