"""Alinhamento de fatores de emissão ao escopo temporal."""

from __future__ import annotations

from collections.abc import Mapping

from emissions.conversion_helpers import uniform_monthly_from_yearly_per_animal
from emissions.exceptions import CalculationError, TemporalInconsistencyError
from emissions.temporal_scope import TemporalScope

# Fatores default legados são definidos com base anual (kg CH4/animal/ano).
DEFAULT_ENTERIC_FACTOR_TEMPORAL_BASIS = TemporalScope.YEARLY
DEFAULT_ENERGY_FACTOR_TEMPORAL_BASIS = TemporalScope.YEARLY


def align_enteric_factors_to_scope(
    factors: Mapping[str, float],
    *,
    temporal_scope: TemporalScope,
    factor_temporal_basis: TemporalScope = DEFAULT_ENTERIC_FACTOR_TEMPORAL_BASIS,
    auto_prorate: bool = True,
) -> dict[str, float]:
    """
    Alinha fatores enteric (kg CH4/animal/período) ao ``temporal_scope`` do cálculo.

    Quando ``factor_temporal_basis`` é anual e o cálculo é mensal, aplica prorratação
    uniforme (/12) se ``auto_prorate=True``; caso contrário levanta erro.
    """
    if factor_temporal_basis == temporal_scope:
        return {k: float(v) for k, v in factors.items()}

    if (
        factor_temporal_basis is TemporalScope.YEARLY
        and temporal_scope is TemporalScope.MONTHLY
    ):
        if not auto_prorate:
            raise TemporalInconsistencyError(
                "Fatores enteric com base anual não podem ser usados com "
                "temporal_scope='monthly' sem prorratação explícita. "
                "Passe fatores mensais ou defina auto_prorate=True."
            )
        return {
            k: uniform_monthly_from_yearly_per_animal(float(v)) for k, v in factors.items()
        }

    if (
        factor_temporal_basis is TemporalScope.MONTHLY
        and temporal_scope is TemporalScope.YEARLY
    ):
        raise TemporalInconsistencyError(
            "Fatores enteric com base mensal não podem ser usados diretamente com "
            "temporal_scope='yearly'. Some 12 meses ou forneça fatores anuais."
        )

    raise CalculationError(
        f"Combinação de factor_temporal_basis={factor_temporal_basis.value!r} e "
        f"temporal_scope={temporal_scope.value!r} não suportada."
    )


def align_energy_factors_to_scope(
    factors: Mapping[str, float],
    *,
    temporal_scope: TemporalScope,
    factor_temporal_basis: TemporalScope = DEFAULT_ENERGY_FACTOR_TEMPORAL_BASIS,
    auto_prorate: bool = True,
) -> dict[str, float]:
    """
    Alinha fatores de energia ao escopo temporal.

    Os defaults legados (kg CO2/unidade) são intensidades por unidade física e normalmente
    não variam com o período; consumo é que deve estar no mesmo período. Esta função
    valida coerência quando o chamador declara base anual explícita em escopo mensal
    (alguns inventários armazenam fatores anuais agregados).
    """
    if factor_temporal_basis == temporal_scope:
        return {k: float(v) for k, v in factors.items()}

    if (
        factor_temporal_basis is TemporalScope.YEARLY
        and temporal_scope is TemporalScope.MONTHLY
    ):
        if not auto_prorate:
            raise TemporalInconsistencyError(
                "Fatores de energia com base anual declarada não podem ser usados com "
                "temporal_scope='monthly' sem prorratação. "
                "Passe fatores alinhados ao período ou defina auto_prorate=True."
            )
        return {
            k: uniform_monthly_from_yearly_per_animal(float(v)) for k, v in factors.items()
        }

    if (
        factor_temporal_basis is TemporalScope.MONTHLY
        and temporal_scope is TemporalScope.YEARLY
    ):
        raise TemporalInconsistencyError(
            "Fatores de energia com base mensal não podem ser usados diretamente com "
            "temporal_scope='yearly'."
        )

    return {k: float(v) for k, v in factors.items()}
