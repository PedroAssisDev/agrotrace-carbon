"""Agregação em CO2e e validação de consistência temporal entre componentes."""

from __future__ import annotations

from emissions.exceptions import CalculationError, TemporalInconsistencyError
from emissions.models import CalculationResult, TotalGhgResult
from emissions.temporal_scope import TemporalScope, require_matching_scope


def calculate_total_ghg_co2e(
    *,
    enteric_ch4: CalculationResult,
    manure_ch4: CalculationResult,
    fertilizer_n2o: CalculationResult,
    energy_co2: CalculationResult,
    gwp_ch4: float,
    gwp_n2o: float,
) -> TotalGhgResult:
    """
    Converte CH4, N2O e CO2 em CO2e e soma (GWP explícito).

    Objetivo:
        Agregar sub-resultados já calculados, garantindo que todos compartilham o mesmo
        :class:`TemporalScope`.

    Parâmetros:
        enteric_ch4, manure_ch4: resultados em kg CH4.
        fertilizer_n2o: resultado em kg N2O.
        energy_co2: resultado em kg CO2.
        gwp_ch4, gwp_n2o: potencial de aquecimento global (kg CO2e por kg de gás).
            Devem ser escolhidos e documentados pelo chamador (ex.: IPCC AR4: 25 e 298).

    Retorno:
        :class:`TotalGhgResult` com totais e parcelas em CO2e (CH4 e N2O) e CO2 fóssil.

    Exceções:
        TemporalInconsistencyError: escopos temporais diferentes entre componentes.
        CalculationError: unidades inesperadas ou GWP inválidos.

    Nota:
        Não há constantes de GWP embutidas nesta função: o chamador deve passá-las explicitamente.
    """
    for name, res, expected_unit in (
        ("enteric_ch4", enteric_ch4, "kg CH4"),
        ("manure_ch4", manure_ch4, "kg CH4"),
        ("fertilizer_n2o", fertilizer_n2o, "kg N2O"),
        ("energy_co2", energy_co2, "kg CO2"),
    ):
        if res.unit != expected_unit:
            raise CalculationError(
                f"{name}: unidade esperada {expected_unit!r}; recebido {res.unit!r}."
            )

    scope = require_matching_scope(
        enteric_ch4.temporal_scope,
        manure_ch4.temporal_scope,
        fertilizer_n2o.temporal_scope,
        energy_co2.temporal_scope,
        context="No total GHG:",
    )

    for gwp_name, gwp_val in (("gwp_ch4", gwp_ch4), ("gwp_n2o", gwp_n2o)):
        if gwp_val is None or not isinstance(gwp_val, (int, float)):
            raise CalculationError(
                f"{gwp_name} deve ser numérico; recebido {type(gwp_val).__name__}."
            )
        if float(gwp_val) < 0 or not float("-inf") < float(gwp_val) < float("inf"):
            raise CalculationError(
                f"{gwp_name} deve ser finito e não negativo; recebido {gwp_val!r}."
            )

    ch4_kg_total = float(enteric_ch4.value) + float(manure_ch4.value)
    n2o_kg = float(fertilizer_n2o.value)
    co2_kg = float(energy_co2.value)

    ch4_co2e = ch4_kg_total * float(gwp_ch4)
    n2o_co2e = n2o_kg * float(gwp_n2o)
    co2e = ch4_co2e + n2o_co2e + co2_kg

    return TotalGhgResult(
        co2e_kg=co2e,
        temporal_scope=scope,
        ch4_co2e_kg=ch4_co2e,
        n2o_co2e_kg=n2o_co2e,
        co2_kg=co2_kg,
    )
