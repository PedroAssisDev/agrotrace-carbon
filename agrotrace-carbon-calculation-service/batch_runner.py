"""
Orquestração em lote (pandas + CSV): delega à pipeline unificada.

Mantém I/O e montagem de parâmetros explícitos a partir de linhas de dados.
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from emissions.temporal_defaults import resolve_days_in_period
from emissions.temporal_scope import TemporalScope
from orchestration.pipeline import compute_row_emissions


def compute_row_results(
    row: Mapping[str, float],
    *,
    temporal_scope: TemporalScope,
    days_in_period: int | None = None,
    enteric_ch4_kg_per_animal: Mapping[str, float] | None = None,
    manure_kg_per_kg_bw_per_day: Mapping[str, float] | None = None,
    manure_ch4_kg_per_kg_manure: Mapping[str, float] | None = None,
    energy_co2_kg_per_unit: Mapping[str, float] | None = None,
    fertilizer_factors: Mapping[str, float] | None = None,
    gwp: Mapping[str, float] | None = None,
    auto_prorate_factors: bool = True,
) -> dict[str, float]:
    """
    Calcula todas as emissões para uma linha, com fatores injetados (ou padrão).

    ``days_in_period`` default alinha-se ao ``temporal_scope`` (365 anual, 30 mensal).
    Fatores enteric/energy default anuais são prorrateados automaticamente em escopo mensal.
    """
    bundle = compute_row_emissions(
        row,
        temporal_scope=temporal_scope,
        days_in_period=days_in_period,
        enteric_ch4_kg_per_animal=enteric_ch4_kg_per_animal,
        manure_kg_per_kg_bw_per_day=manure_kg_per_kg_bw_per_day,
        manure_ch4_kg_per_kg_manure=manure_ch4_kg_per_kg_manure,
        energy_co2_kg_per_unit=energy_co2_kg_per_unit,
        fertilizer_factors=fertilizer_factors,
        gwp=gwp,
        auto_prorate_factors=auto_prorate_factors,
    )
    return bundle.to_flat_dict()


def add_emissions_columns(
    farm_data: pd.DataFrame,
    *,
    temporal_scope: TemporalScope,
    days_in_period: int | None = None,
    **kwargs: object,
) -> pd.DataFrame:
    """Adiciona colunas de emissão ao DataFrame (uma linha por chamada a ``compute_row_results``)."""
    resolved_days = resolve_days_in_period(temporal_scope, days_in_period)
    rows_out: list[dict[str, float]] = []
    for _, row in farm_data.iterrows():
        r = compute_row_results(
            row,
            temporal_scope=temporal_scope,
            days_in_period=resolved_days,
            **{k: v for k, v in kwargs.items() if v is not None},
        )
        rows_out.append(r)
    emissions_df = pd.DataFrame(rows_out)
    return pd.concat([farm_data.reset_index(drop=True), emissions_df], axis=1)


def run_csv_pipeline(
    input_file_path: str,
    output_file_path: str,
    *,
    temporal_scope: TemporalScope = TemporalScope.ANNUAL,
    days_in_period: int | None = None,
    sep: str = ";",
    **kwargs: object,
) -> pd.DataFrame:
    """Lê CSV, calcula emissões, grava CSV."""
    farm_data = pd.read_csv(input_file_path, sep=sep)
    final_data = add_emissions_columns(
        farm_data,
        temporal_scope=temporal_scope,
        days_in_period=days_in_period,
        **kwargs,
    )
    final_data.to_csv(output_file_path, sep=sep, index=False)
    return final_data
