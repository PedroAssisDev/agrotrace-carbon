"""
Fatores de exemplo e chaves padrão (IPCC 2006 / exemplos do legado).

Estes valores **não** estão embutidos nas funções de cálculo: são retornados aqui para que
o chamador os injete explicitamente (CSV, banco, API ou testes).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from emissions.exceptions import CalculationError

# Categorias animais usadas no modelo simplificado legado
ANIMAL_CATEGORIES: tuple[str, ...] = (
    "Lactating_Cows",
    "Dry_Cows",
    "Heifers",
    "Calves",
    "Bulls",
)

ENERGY_VECTORS: tuple[str, ...] = (
    "Diesel",
    "Gasoline",
    "Electricity_Grid",
    "Photovoltaic_Energy",
)

# Coluna legada: valor em **kg N aplicado no período**, não massa de fertilizante comercial.
NITROGEN_APPLIED_KG_COLUMN = "Non_Organic_Fertilizer"

MILK_LITERS_COLUMN = "Milk_Liters"
MILK_KG_FPCM_COLUMN = "Milk_kg_FPCM"


def _extract_optional_float(row: Mapping[str, Any], key: str) -> float | None:
    if key not in row:
        return None
    value = row[key]
    if value is None or (isinstance(value, float) and str(value) == "nan"):
        return None
    return float(value)


def _extract_required_float(row: Mapping[str, Any], key: str, *, label: str) -> float:
    if key not in row:
        raise CalculationError(
            f"Coluna obrigatória {label!r} ({key!r}) em falta na linha de dados."
        )
    try:
        return float(row[key])
    except (TypeError, ValueError) as exc:
        raise CalculationError(
            f"Coluna {label!r} ({key!r}) deve ser numérica; recebido {row[key]!r}."
        ) from exc


def default_enteric_ch4_kg_per_animal_yearly() -> dict[str, float]:
    """
    Fatores legados interpretados como kg CH4 por animal **por ano**.

    Unidade: kg CH4 / (animal · ano)
    """
    return {
        "Lactating_Cows": 100.0,
        "Dry_Cows": 50.0,
        "Heifers": 30.0,
        "Calves": 20.0,
        "Bulls": 10.0,
    }


# Nome canônico (annual); yearly permanece como alias de leitura/legado.
default_enteric_ch4_kg_per_animal_annual = default_enteric_ch4_kg_per_animal_yearly


def default_manure_kg_per_kg_bw_per_day() -> dict[str, float]:
    """kg esterco / (kg peso vivo · dia) — valores didáticos do legado."""
    return {
        "Lactating_Cows": 0.08,
        "Dry_Cows": 0.07,
        "Heifers": 0.06,
        "Calves": 0.05,
        "Bulls": 0.09,
    }


def default_manure_ch4_kg_per_kg_manure() -> dict[str, float]:
    """
    kg CH4 por kg de esterco úmido — defaults didáticos recalibrados.

    Os valores legados (~0,10–0,20) foram definidos antes da multiplicação explícita
    por ``days_in_period`` e implicavam ~17% da massa úmida convertida em CH4
    (~2 700 kg CH4/vaca lactante/ano), fisicamente inviável e ~27× a entérica.

    Os valores abaixo mantêm a fórmula ``n×w×md×ef×dias`` e produzem ordem de
    grandeza compatível com IPCC Tier 1 para manejo de dejetos leiteiros
    (~10–20 kg CH4/cabeça/ano para lactante 550 kg com md=0,08):
    ``550 × 0,08 × 0,001 × 365 ≈ 16 kg CH4/ano``.
    """
    return {
        "Lactating_Cows": 0.001,
        "Dry_Cows": 0.0008,
        "Heifers": 0.0007,
        "Calves": 0.0006,
        "Bulls": 0.0012,
    }


def default_energy_co2_kg_per_unit_yearly_basis() -> dict[str, float]:
    """
    Fatores legados para CO2 por unidade de consumo.

    Diesel/Gasolina: kg CO2 / L. Eletricidade: kg CO2 / kWh. Fotovoltaico: 0.
    """
    return {
        "Diesel": 2.68,
        "Gasoline": 2.31,
        "Electricity_Grid": 0.233,
        "Photovoltaic_Energy": 0.0,
    }


default_energy_co2_kg_per_unit_annual_basis = default_energy_co2_kg_per_unit_yearly_basis


def default_fertilizer_factors() -> dict[str, float]:
    """
    Fatores do legado para N2O a partir de N aplicado.

    - direct_n2o_emission_factor: kg N2O / kg N
    - indirect_n2o_emission_factor: kg N2O / kg N volatilizado
    - fraction_n_volatilized: fração do N aplicado volatilizada (antes fixa em 0,1)
    """
    return {
        "direct_n2o_emission_factor": 0.01,
        "indirect_n2o_emission_factor": 0.005,
        "fraction_n_volatilized": 0.1,
    }


def gwp_ipcc_ar4() -> dict[str, float]:
    """
    GWP AR4 (caixa de ferramentas legada).

    Documentação: IPCC AR4; valores adimensionais kg CO2e por kg de gás.
    """
    return {"CH4": 25.0, "N2O": 298.0}


def extract_headcounts(
    row: Mapping[str, Any],
    categories: tuple[str, ...],
) -> dict[str, float]:
    """Lê contagens animais a partir de um mapeamento estilo linha de planilha."""
    return {
        c: _extract_required_float(row, c, label=f"headcount[{c}]") for c in categories
    }


def extract_body_weights_kg(
    row: Mapping[str, Any],
    categories: tuple[str, ...],
) -> dict[str, float]:
    """Lê pesos ``{Categoria}_Weight`` (kg) como no legado."""
    return {
        c: _extract_required_float(row, f"{c}_Weight", label=f"body_weight[{c}]")
        for c in categories
    }


def extract_energy_consumption(
    row: Mapping[str, Any],
    vectors: tuple[str, ...],
) -> dict[str, float]:
    return {
        v: _extract_required_float(row, v, label=f"energy[{v}]") for v in vectors
    }


def extract_nitrogen_applied_kg(row: Mapping[str, Any]) -> float:
    """
    Massa de N inorgânico aplicada no período (kg N).

    A coluna ``Non_Organic_Fertilizer`` contém **kg N**, não kg de produto fertilizante.
    """
    return _extract_required_float(
        row,
        NITROGEN_APPLIED_KG_COLUMN,
        label="nitrogen_applied_kg",
    )


def extract_milk_liters(row: Mapping[str, Any]) -> float | None:
    """Produção de leite no período (L), se disponível."""
    return _extract_optional_float(row, MILK_LITERS_COLUMN)


def extract_milk_kg_fpcm(row: Mapping[str, Any]) -> float | None:
    """Produção de leite corrigido FPCM no período (kg), se disponível."""
    return _extract_optional_float(row, MILK_KG_FPCM_COLUMN)
