"""
Conversões explícitas entre períodos — nunca aplicadas automaticamente nos núcleos de cálculo.
"""


def uniform_monthly_from_yearly_per_animal(yearly_kg_ch4_per_animal: float) -> float:
    """
    Prorratação uniforme em 12 meses: kg CH4/(animal·mês).

    Use apenas quando a regra de negócio aceitar divisão simples do fator anual.
    """
    return float(yearly_kg_ch4_per_animal) / 12.0


def sum_monthly_values(monthly_values: list[float]) -> float:
    """Soma explícita de valores mensais para obter um total anual (caminho (a))."""
    return float(sum(monthly_values))
