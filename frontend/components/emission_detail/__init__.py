"""Componentes da tela Cálculos de Emissão — detalhamento técnico."""

from components.emission_detail.badges import EmissionCalcHeaderBadges
from components.emission_detail.cards import EmissionOverviewCards, EmissionVariationCards
from components.emission_detail.data_origin import EmissionDataOriginPanel
from components.emission_detail.factors import EmissionFactorsTable
from components.emission_detail.formulas import EmissionFormulaAccordion
from components.emission_detail.gas import EmissionGasBreakdown
from components.emission_detail.next_action import EmissionNextAction
from components.emission_detail.scope import ScopeBadge
from components.emission_detail.sources import (
    EmissionSourceDetailAccordion,
    EmissionSourceLineChart,
    EmissionSourceRanking,
    EntericTierComparisonPanel,
)
from components.emission_detail.temporal import EmissionTemporalSection

__all__ = [
    "EmissionCalcHeaderBadges",
    "EmissionOverviewCards",
    "EmissionTemporalSection",
    "EmissionSourceRanking",
    "EmissionSourceLineChart",
    "EmissionGasBreakdown",
    "EmissionSourceDetailAccordion",
    "EntericTierComparisonPanel",
    "EmissionFormulaAccordion",
    "EmissionFactorsTable",
    "EmissionVariationCards",
    "EmissionDataOriginPanel",
    "EmissionNextAction",
    "ScopeBadge",
]
