"""Consolidação auditável de resultados mensais em totais anuais."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from emissions.exceptions import CalculationError, TemporalInconsistencyError
from emissions.models import CalculationResult, TotalGhgResult
from emissions.temporal_scope import TemporalScope, require_matching_scope


class ConsolidationType(str, Enum):
    """Tipo de agregação temporal (compatível com traceability-service)."""

    SUM_OF_MONTHLY = "sum_of_monthly"


@dataclass(frozen=True)
class ConsolidatedAnnualResult:
    """Resultado anual consolidado a partir de parcelas mensais."""

    component: CalculationResult
    consolidation_type: ConsolidationType
    source_count: int


@dataclass(frozen=True)
class ConsolidatedAnnualGhgResult:
    """Total anual CO2e consolidado a partir de totais mensais."""

    total: TotalGhgResult
    consolidation_type: ConsolidationType
    source_count: int


def consolidate_monthly_calculation_results(
    monthly_results: list[CalculationResult],
    *,
    consolidation_type: ConsolidationType = ConsolidationType.SUM_OF_MONTHLY,
) -> ConsolidatedAnnualResult:
    """
    Soma resultados mensais homogéneos num total anual.

    Exige que todos os itens tenham ``TemporalScope.MONTHLY`` e a mesma unidade.
    """
    if not monthly_results:
        raise CalculationError(
            "consolidate_monthly_calculation_results: lista mensal não pode ser vazia."
        )
    if len(monthly_results) != 12:
        raise CalculationError(
            f"consolidate_monthly_calculation_results: esperados 12 meses; "
            f"recebidos {len(monthly_results)}."
        )

    scope = require_matching_scope(
        *(r.temporal_scope for r in monthly_results),
        context="Consolidação mensal:",
    )
    if scope is not TemporalScope.MONTHLY:
        raise TemporalInconsistencyError(
            f"Consolidação mensal→anual exige entradas mensais; recebido {scope.value!r}."
        )

    reference_unit = monthly_results[0].unit
    reference_description = monthly_results[0].description
    for i, result in enumerate(monthly_results[1:], start=2):
        if result.unit != reference_unit:
            raise CalculationError(
                f"Inconsistência de unidade no mês {i}: esperado {reference_unit!r}, "
                f"recebido {result.unit!r}."
            )

    total_value = sum(float(r.value) for r in monthly_results)
    return ConsolidatedAnnualResult(
        component=CalculationResult(
            value=total_value,
            unit=reference_unit,
            temporal_scope=TemporalScope.YEARLY,
            description=reference_description,
        ),
        consolidation_type=consolidation_type,
        source_count=len(monthly_results),
    )


def consolidate_monthly_ghg_totals(
    monthly_totals: list[TotalGhgResult],
    *,
    consolidation_type: ConsolidationType = ConsolidationType.SUM_OF_MONTHLY,
) -> ConsolidatedAnnualGhgResult:
    """Soma totais mensais CO2e num total anual auditável."""
    if not monthly_totals:
        raise CalculationError(
            "consolidate_monthly_ghg_totals: lista mensal não pode ser vazia."
        )
    if len(monthly_totals) != 12:
        raise CalculationError(
            f"consolidate_monthly_ghg_totals: esperados 12 meses; "
            f"recebidos {len(monthly_totals)}."
        )

    scope = require_matching_scope(
        *(t.temporal_scope for t in monthly_totals),
        context="Consolidação CO2e mensal:",
    )
    if scope is not TemporalScope.MONTHLY:
        raise TemporalInconsistencyError(
            f"Consolidação CO2e mensal→anual exige entradas mensais; recebido {scope.value!r}."
        )

    return ConsolidatedAnnualGhgResult(
        total=TotalGhgResult(
            co2e_kg=sum(float(t.co2e_kg) for t in monthly_totals),
            temporal_scope=TemporalScope.YEARLY,
            ch4_co2e_kg=sum(float(t.ch4_co2e_kg) for t in monthly_totals),
            n2o_co2e_kg=sum(float(t.n2o_co2e_kg) for t in monthly_totals),
            co2_kg=sum(float(t.co2_kg) for t in monthly_totals),
        ),
        consolidation_type=consolidation_type,
        source_count=len(monthly_totals),
    )
