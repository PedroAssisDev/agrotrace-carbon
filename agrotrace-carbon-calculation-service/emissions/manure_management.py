"""Cálculo de CH4 por manejo de esterco (funções puras)."""

from __future__ import annotations

from collections.abc import Mapping

from emissions.exceptions import CalculationError
from emissions.models import CalculationResult
from emissions.temporal_scope import TemporalScope
from emissions.validators import (
    require_same_keys,
    validate_days_in_period,
    validate_mapping_non_negative,
)


def calculate_manure_management_ch4(
    *,
    temporal_scope: TemporalScope,
    headcounts_by_category: Mapping[str, float],
    body_weight_kg_by_category: Mapping[str, float],
    manure_kg_per_kg_body_weight_per_day: Mapping[str, float],
    ch4_kg_per_kg_manure: Mapping[str, float],
    days_in_period: int,
) -> CalculationResult:
    """
    Calcula emissões de CH4 por manejo de esterco (modelo proporcional a massa de esterco).

    Referência conceitual: IPCC 2006, Vol. 4, Caps. 10 e 11 (forma didática/simplificada).

    Objetivo:
        Estimar kg CH4 no período a partir de produção diária de esterco por peso vivo
        e fator CH4 por massa de esterco, **explicitamente** multiplicado pelos dias do período.

    Parâmetros:
        temporal_scope: ``monthly`` ou ``annual``; deve ser consistente com ``days_in_period``.
        headcounts_by_category: número de animais por categoria (>= 0).
        body_weight_kg_by_category: peso médio por animal (kg) na mesma granularidade temporal
            da contagem (ex.: peso representativo do mês ou média anual).
        manure_kg_per_kg_body_weight_per_day: kg esterco / (kg peso vivo · dia).
        ch4_kg_per_kg_manure: kg CH4 por kg de esterco gerado.
        days_in_period: número de dias cobertos pelo cálculo (ex.: 30 mensal, 365 anual).

    Unidades:
        Resultado: kg CH4 no período.

    Exceções:
        CalculationError: mapeamentos vazios, chaves inconsistentes, valores negativos.
        TemporalInconsistencyError: ``days_in_period`` incompatível com ``temporal_scope``.

    Divergência em relação à implementação anterior:
        O código legado definia ``days_per_year = 365`` mas **não multiplicava** a soma por
        dias; a nova versão exige ``days_in_period`` e aplica a multiplicação, coerente com
        fatores declarados \"por dia\".
    """
    validate_days_in_period(temporal_scope, days_in_period)
    validate_mapping_non_negative(headcounts_by_category, "headcounts_by_category")
    validate_mapping_non_negative(body_weight_kg_by_category, "body_weight_kg_by_category")
    validate_mapping_non_negative(
        manure_kg_per_kg_body_weight_per_day,
        "manure_kg_per_kg_body_weight_per_day",
    )
    validate_mapping_non_negative(ch4_kg_per_kg_manure, "ch4_kg_per_kg_manure")

    for label, m in (
        ("headcounts_by_category", headcounts_by_category),
        ("body_weight_kg_by_category", body_weight_kg_by_category),
        ("manure_kg_per_kg_body_weight_per_day", manure_kg_per_kg_body_weight_per_day),
        ("ch4_kg_per_kg_manure", ch4_kg_per_kg_manure),
    ):
        if not m:
            raise CalculationError(f"{label} não pode ser vazio.")

    require_same_keys(
        headcounts_by_category,
        body_weight_kg_by_category,
        "headcounts_by_category",
        "body_weight_kg_by_category",
    )
    require_same_keys(
        headcounts_by_category,
        manure_kg_per_kg_body_weight_per_day,
        "headcounts_by_category",
        "manure_kg_per_kg_body_weight_per_day",
    )
    require_same_keys(
        headcounts_by_category,
        ch4_kg_per_kg_manure,
        "headcounts_by_category",
        "ch4_kg_per_kg_manure",
    )

    total = 0.0
    for k in headcounts_by_category:
        n = float(headcounts_by_category[k])
        w = float(body_weight_kg_by_category[k])
        md = float(manure_kg_per_kg_body_weight_per_day[k])
        ef = float(ch4_kg_per_kg_manure[k])
        total += n * w * md * ef * float(days_in_period)

    return CalculationResult(
        value=total,
        unit="kg CH4",
        temporal_scope=temporal_scope,
        description="Manure management CH4",
    )
