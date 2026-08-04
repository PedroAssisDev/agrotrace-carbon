"""Cálculo de N2O por fertilização (funções puras)."""

from __future__ import annotations

from emissions.exceptions import CalculationError
from emissions.models import CalculationResult
from emissions.temporal_scope import TemporalScope
from emissions.validators import require_non_negative


def calculate_fertilizer_n2o(
    *,
    temporal_scope: TemporalScope,
    nitrogen_applied_kg: float,
    direct_n2o_emission_factor: float,
    indirect_n2o_emission_factor: float,
    fraction_n_volatilized: float,
) -> CalculationResult:
    """
    Calcula emissões de N2O a partir de aplicação de fertilizante nitrogenado.

    Referência conceitual: IPCC 2006, Vol. 4, Cap. 11 (forma simplificada).

    Objetivo:
        Estimar kg N2O no período (mensal ou anual) a partir da massa de N aplicada
        e fatores de emissão direta e indireta (volatilização), **todos injetados**.

    Parâmetros:
        temporal_scope: granularidade das massas e do resultado.
        nitrogen_applied_kg: massa de N aplicada no período (kg N).
        direct_n2o_emission_factor: kg N2O emitidos / kg N aplicado (via deposição direta).
        indirect_n2o_emission_factor: kg N2O / kg N volatilizado (via rota indireta).
        fraction_n_volatilized: fração adimensional do N aplicado que volatiliza (0..1).

    Retorno:
        :class:`CalculationResult` com ``value`` em kg N2O.

    Exceções:
        CalculationError: valores negativos, fração fora de [0, 1], ou não finitos.

    Nota:
        A implementação legado fixava fração de volatilização em 0,1; aqui o valor é parâmetro.
    """
    require_non_negative("nitrogen_applied_kg", float(nitrogen_applied_kg))
    require_non_negative("direct_n2o_emission_factor", float(direct_n2o_emission_factor))
    require_non_negative("indirect_n2o_emission_factor", float(indirect_n2o_emission_factor))
    require_non_negative("fraction_n_volatilized", float(fraction_n_volatilized))
    if float(fraction_n_volatilized) > 1:
        raise CalculationError(
            "fraction_n_volatilized não pode ser maior que 1; "
            f"recebido {fraction_n_volatilized!r}."
        )

    direct = float(nitrogen_applied_kg) * float(direct_n2o_emission_factor)
    indirect = (
        float(nitrogen_applied_kg)
        * float(fraction_n_volatilized)
        * float(indirect_n2o_emission_factor)
    )
    total = direct + indirect
    return CalculationResult(
        value=total,
        unit="kg N2O",
        temporal_scope=temporal_scope,
        description="Fertilizer N2O",
    )
