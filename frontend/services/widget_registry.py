"""Registry declarativo de widgets gerenciais (KPIs e gráficos)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


WidgetType = Literal["kpi", "chart", "section"]
SectionKey = Literal["summary", "productivity", "emissions", "sustainability", "management", "business", "data_quality", "pipeline", "auditability"]
Priority = Literal["P1", "P2", "P3"]


@dataclass(frozen=True)
class WidgetSpec:
    widget_id: str
    title: str
    widget_type: WidgetType
    section: SectionKey
    kpi_key: str | None = None
    icon: str = "fas fa-chart-bar"
    color: str = "success"
    required_fields: tuple[str, ...] = ()
    applicable_farm_types: tuple[str, ...] = ("dairy", "mixed")
    status_dependency: tuple[str, ...] = ()
    official_only: bool = False
    priority: Priority = "P1"
    screens: tuple[str, ...] = ("/",)
    chart_key: str | None = None


_EXECUTIVE_KPIS: list[WidgetSpec] = [
    WidgetSpec("co2e_total", "Emissões totais (kg CO₂e)", "kpi", "summary", "co2e_total_kg",
               "fas fa-cloud", "danger", ("co2e_total_kg",), status_dependency=("CalculationPreliminary", "Published")),
    WidgetSpec("intensity", "Intensidade (kg CO₂e/L)", "kpi", "emissions", "intensity_kg_per_liter",
               "fas fa-tint", "primary", ("milk_production", "co2e_total_kg"),
               applicable_farm_types=("dairy",), status_dependency=("CalculationPreliminary", "Published")),
    WidgetSpec("milk_total", "Produção de leite (L)", "kpi", "productivity", "total_milk_liters",
               "fas fa-cheese", "success", ("milk_production",)),
    WidgetSpec("main_source", "Principal fonte emissora", "kpi", "emissions", "main_source",
               "fas fa-fire", "danger", ("co2e_total_kg",), status_dependency=("CalculationPreliminary", "Published")),
    WidgetSpec("cycles_pending", "Aguardando aprovação", "kpi", "pipeline", "awaiting_approval",
               "fas fa-user-clock", "warning", status_dependency=("PendingApproval",), screens=("/",)),
]

_INDICATOR_SECTIONS: list[tuple[str, SectionKey, str]] = [
    ("productivity", "productivity", "Produtividade"),
    ("management", "management", "Manejo"),
    ("emissions", "emissions", "Emissões"),
    ("sustainability", "sustainability", "Sustentabilidade"),
    ("business", "business", "Gerenciamento"),
    ("data_quality", "data_quality", "Qualidade dos dados"),
]

WIDGET_SPECS: list[WidgetSpec] = list(_EXECUTIVE_KPIS)


def get_widget_specs_for_screen(screen: str) -> list[WidgetSpec]:
    specs = [w for w in WIDGET_SPECS if screen in w.screens or screen == "*"]
    order = {"P1": 0, "P2": 1, "P3": 2}
    return sorted(specs, key=lambda w: order.get(w.priority, 9))


def register_indicator_kpis(section_key: str, kpi_keys: list[tuple[str, str, str, str, tuple[str, ...]]]) -> None:
    """Registra KPIs de indicador_service para renderização condicional."""
    global WIDGET_SPECS
    for kpi_key, title, icon, color, fields in kpi_keys:
        WIDGET_SPECS.append(WidgetSpec(
            f"{section_key}_{kpi_key}", title, "kpi", section_key, kpi_key,
            icon, color, fields, screens=("/indicators",), priority="P2",
        ))
