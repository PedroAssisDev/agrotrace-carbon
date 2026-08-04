"""Cálculo de CO2 por consumo de energia (funções puras)."""

from __future__ import annotations

from collections.abc import Mapping

from emissions.exceptions import CalculationError
from emissions.models import CalculationResult
from emissions.temporal_scope import TemporalScope
from emissions.validators import require_same_keys, validate_mapping_non_negative


def calculate_energy_co2(
    *,
    temporal_scope: TemporalScope,
    consumption_by_vector: Mapping[str, float],
    co2_kg_per_unit_consumption: Mapping[str, float],
) -> CalculationResult:
    """
    Calcula emissões de CO2 a partir de consumo por vetor energético.

    Referência conceitual: IPCC 2006, Vol. 2, Cap. 2 (fatores de emissão por combustível/eletricidade).

    Objetivo:
        Somar ``consumo[v] * fator[v]`` para cada vetor, com fatores explícitos.

    Parâmetros:
        temporal_scope: período ao qual se referem os consumos (mensal ou anual).
        consumption_by_vector:
            Quantidade consumida no período por vetor (ex.: L de diesel, kWh).
            A unidade física deve ser a mesma usada na definição dos fatores.
        co2_kg_per_unit_consumption:
            kg CO2 por unidade de consumo (mesma unidade que ``consumption_by_vector``).

    Retorno:
        :class:`CalculationResult` com ``value`` em kg CO2.

    Exceções:
        CalculationError: mapeamento vazio, chaves divergentes ou valores negativos.
    """
    validate_mapping_non_negative(consumption_by_vector, "consumption_by_vector")
    validate_mapping_non_negative(co2_kg_per_unit_consumption, "co2_kg_per_unit_consumption")
    require_same_keys(
        consumption_by_vector,
        co2_kg_per_unit_consumption,
        "consumption_by_vector",
        "co2_kg_per_unit_consumption",
    )
    if not consumption_by_vector:
        raise CalculationError(
            "consumption_by_vector não pode ser vazio: informe ao menos um vetor energético."
        )

    total = sum(
        float(consumption_by_vector[k]) * float(co2_kg_per_unit_consumption[k])
        for k in consumption_by_vector
    )
    return CalculationResult(
        value=total,
        unit="kg CO2",
        temporal_scope=temporal_scope,
        description="Energy CO2",
    )
