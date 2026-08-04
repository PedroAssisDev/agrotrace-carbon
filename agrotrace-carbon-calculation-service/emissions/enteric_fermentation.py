"""Cálculo de CH4 por fermentação entérica (funções puras)."""

from __future__ import annotations

from collections.abc import Mapping

from emissions.exceptions import CalculationError
from emissions.models import CalculationResult
from emissions.temporal_scope import TemporalScope
from emissions.validators import require_same_keys, validate_mapping_non_negative


def calculate_enteric_fermentation_ch4(
    *,
    temporal_scope: TemporalScope,
    headcounts_by_category: Mapping[str, float],
    ch4_kg_per_animal_in_period: Mapping[str, float],
) -> CalculationResult:
    """
    Calcula emissões de CH4 por fermentação entérica.

    Referência conceitual: IPCC 2006, Vol. 4, Cap. 10 (abordagem simplificada por categoria).

    Objetivo:
        Estimar massa de CH4 emitida no período (mensal ou anual) a partir de
        cabeças por categoria e fatores de emissão **já alinhados ao mesmo período**.

    Parâmetros:
        temporal_scope:
            ``monthly``: use contagens e fatores referentes a um único mês.
            ``yearly``: use contagens e fatores referentes ao ano completo
            (não some implicitamente meses; isso é responsabilidade de quem chama).
        headcounts_by_category:
            Número de animais por categoria (adimensional, >= 0).
            Unidade temporal implícita: a mesma de ``temporal_scope``.
        ch4_kg_per_animal_in_period:
            Massa de CH4 (kg) por animal **no mesmo período** que ``temporal_scope``.
            Ex.: kg CH4/animal/mês (mensal) ou kg CH4/animal/ano (anual).

    Retorno:
        :class:`CalculationResult` com ``value`` em kg CH4 e ``unit`` ``\"kg CH4\"``.

    Exceções:
        CalculationError: chaves divergentes, valores negativos ou não numéricos.

    Nota sobre agregação anual:
        O total anual pode ser (a) soma de 12 resultados mensais com entradas mensais, ou
        (b) um único cálculo com dados anuais — ambos são válidos desde que os fatores e
        contagens correspondam ao mesmo tipo de período (sem mistura implícita).
    """
    validate_mapping_non_negative(headcounts_by_category, "headcounts_by_category")
    validate_mapping_non_negative(ch4_kg_per_animal_in_period, "ch4_kg_per_animal_in_period")
    require_same_keys(
        headcounts_by_category,
        ch4_kg_per_animal_in_period,
        "headcounts_by_category",
        "ch4_kg_per_animal_in_period",
    )
    if not headcounts_by_category:
        raise CalculationError(
            "headcounts_by_category não pode ser vazio: defina ao menos uma categoria animal."
        )

    total = sum(
        float(headcounts_by_category[k]) * float(ch4_kg_per_animal_in_period[k])
        for k in headcounts_by_category
    )
    return CalculationResult(
        value=total,
        unit="kg CH4",
        temporal_scope=temporal_scope,
        description="Enteric fermentation CH4",
    )
