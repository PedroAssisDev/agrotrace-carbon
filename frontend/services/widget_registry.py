"""Registry declarativo de widgets gerenciais (KPIs e gráficos)."""

from __future__ import annotations

from dataclasses import dataclass
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
    subtitle: str = ""
    value_format: str = ""


_EXECUTIVE_KPIS: list[WidgetSpec] = [
    WidgetSpec(
        "co2e_total_t", "Emissões totais", "kpi", "summary", "co2e_total_t",
        "fas fa-cloud", "danger", ("co2e_total_kg",),
        subtitle="t CO₂e no período selecionado",
        value_format="co2e_t",
    ),
    WidgetSpec(
        "milk_total", "Produção total", "kpi", "summary", "total_milk_liters",
        "fas fa-tint", "success", ("milk_production",),
        subtitle="L de leite no período selecionado",
        value_format="liters",
    ),
    WidgetSpec(
        "intensity_consolidated", "Intensidade de emissão", "kpi", "summary",
        "intensity_consolidated_kg_per_l",
        "fas fa-chart-line", "primary", ("milk_production", "co2e_total_kg"),
        subtitle="kg CO₂e/L",
        value_format="intensity",
    ),
    WidgetSpec(
        "period_status", "Status do período", "kpi", "summary", "period_status_label",
        "fas fa-info-circle", "info",
        subtitle="situação do período analisado",
        value_format="status",
    ),
    WidgetSpec(
        "cycles_pending", "Aguardando aprovação", "kpi", "pipeline", "awaiting_approval",
        "fas fa-user-clock", "warning",
        status_dependency=("PendingApproval",),
        screens=("/",),
        priority="P2",
    ),
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
