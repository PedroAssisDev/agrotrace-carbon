"""Modelos de dados (DTOs) para entradas e resultados de cálculos."""

from __future__ import annotations

from dataclasses import dataclass

from emissions.temporal_scope import TemporalScope


@dataclass(frozen=True)
class CalculationResult:
    """
    Resultado numérico de um cálculo puro, com metadados de unidade e tempo.

    Attributes:
        value: Magnitude calculada (não arredondada pela camada de cálculo).
        unit: Unidade física (ex.: ``kg CH4``, ``kg N2O``, ``kg CO2``).
        temporal_scope: Granularidade temporal à qual o valor se refere.
        description: Texto curto opcional (ex.: nome do subtipo de emissão).
    """

    value: float
    unit: str
    temporal_scope: TemporalScope
    description: str = ""


@dataclass(frozen=True)
class TotalGhgResult:
    """Total em CO2e com decomposição opcional por gás convertido."""

    co2e_kg: float
    temporal_scope: TemporalScope
    ch4_co2e_kg: float
    n2o_co2e_kg: float
    co2_kg: float
