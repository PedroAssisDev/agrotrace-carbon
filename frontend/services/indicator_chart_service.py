"""Séries e componentes gráficos para indicadores."""

from __future__ import annotations

from typing import Any

from services.cycle_state import PIPELINE_STEP_DEFS
from services.indicator_extraction_service import num
from utils.formatting import NA as _NA

STEP_BY_LABEL = {s.step_id: s.label.split(". ", 1)[-1][:24] for s in PIPELINE_STEP_DEFS}


def build_dashboard_chart_series(indicators: dict, cycles: list[dict]) -> dict:
    prod = indicators.get("productivity") or {}
    em = indicators.get("emissions") or {}
    sus = indicators.get("sustainability") or {}
    mgmt = indicators.get("management") or {}
    biz = indicators.get("business") or {}
    qual = indicators.get("data_quality") or {}
    pipe = indicators.get("pipeline") or {}
    audit = indicators.get("auditability") or {}

    def _lv(items: list[dict]) -> tuple[list[str], list[float]]:
        labels, values = [], []
        for it in items or []:
            v = it.get("value")
            if v is not None:
                labels.append(str(it.get("label", "")))
                values.append(float(v))
        return labels, values

    milk_l, milk_v = _lv(prod.get("milk_by_period"))
    prop_l, prop_v = _lv(prod.get("milk_by_property"))
    co2e_l, co2e_v = _lv(em.get("co2e_by_period"))
    co2e_t_l, co2e_t_v = _lv(em.get("co2e_by_period_t"))
    int_l, int_v = _lv(em.get("intensity_by_period"))
    cp_l, cp_v = _lv(sus.get("carbon_productivity_series"))
    eff_l, eff_v = _lv(sus.get("efficiency_by_property"))
    feed_l, feed_v = _lv(mgmt.get("feed_top5"))
    comp = em.get("period_comparison") or {}
    rb = qual.get("record_breakdown") or {}

    return {
        "productivity": {
            "milk_by_period": {"labels": milk_l, "values": milk_v},
            "operational_milk_by_day": {
                "labels": [it.get("label", "") for it in (prod.get("operational_milk_by_day") or []) if it.get("value") is not None],
                "values": [float(it["value"]) for it in (prod.get("operational_milk_by_day") or []) if it.get("value") is not None],
            },
            "milk_by_property": {"labels": prop_l, "values": prop_v},
            "show_by_property": len(prop_v) > 1,
            "quality": {
                "labels": ["Gordura %", "Proteína %"],
                "values": [
                    prod.get("milk_fat_pct") if prod.get("milk_fat_pct") != _NA else None,
                    prod.get("milk_protein_pct") if prod.get("milk_protein_pct") != _NA else None,
                ],
            },
        },
        "emissions": {
            "co2e_by_period": {"labels": co2e_l, "values": co2e_v},
            "co2e_by_period_t": {"labels": co2e_t_l, "values": co2e_t_v},
            "intensity_by_period": {"labels": int_l, "values": int_v},
            "by_source": em.get("by_source") or {},
            "by_gas": em.get("by_gas") or {},
            "period_comparison": comp,
        },
        "sustainability": {
            "carbon_productivity": {"labels": cp_l, "values": cp_v},
            "intensity": {"labels": int_l, "values": int_v},
            "efficiency_by_property": {"labels": eff_l, "values": eff_v},
            "co2e_per_hectare": sus.get("co2e_per_hectare"),
        },
        "management": {
            "feed_top5": {"labels": feed_l, "values": feed_v},
            "fertilizer_split": {
                "labels": ["Orgânico", "Químico"],
                "values": [
                    mgmt.get("organic_fertilizer_kg") if mgmt.get("organic_fertilizer_kg") != _NA else None,
                    mgmt.get("non_organic_fertilizer_kg") if mgmt.get("non_organic_fertilizer_kg") != _NA else None,
                ],
            },
            "energy_split": {
                "labels": ["Rede", "Fotovoltaica"],
                "values": [
                    mgmt.get("electricity_grid_kwh") if mgmt.get("electricity_grid_kwh") != _NA else None,
                    mgmt.get("photovoltaic_energy_kwh") if mgmt.get("photovoltaic_energy_kwh") != _NA else None,
                ],
            },
        },
        "business": {
            "pipeline_summary": {
                "labels": ["Em andamento", "Aguard. aprovação", "Aprovados"],
                "values": [
                    biz.get("cycles_in_progress"),
                    biz.get("awaiting_approval"),
                    biz.get("cycles_approved"),
                ],
            },
        },
        "data_quality": {
            "record_breakdown": rb,
            "errors_by_step": qual.get("errors_by_step") or {},
            "completeness_trend": {
                "labels": [x["period_label"] for x in qual.get("completeness_trend") or [] if x.get("pct") is not None],
                "values": [x["pct"] for x in qual.get("completeness_trend") or [] if x.get("pct") is not None],
            },
        },
        "pipeline": {
            "cycles_by_status": pipe.get("by_status") or {},
            "cycles_by_step": {STEP_BY_LABEL.get(k, k): v for k, v in (pipe.get("by_step") or {}).items()},
        },
        "auditability": {
            "packages_by_status": audit.get("packages_by_status") or {},
            "verification_split": audit.get("verification_split") or {},
        },
    }


def bucket_intensity(row: dict) -> float | None:
    intensity = num(row.get("intensity"))
    if intensity is not None:
        return intensity
    co2e = num(row.get("co2e_kg"))
    milk = num(row.get("milk_liters"))
    if co2e is not None and milk and milk > 0:
        return co2e / milk
    return None


def build_executive_temporal_series(indicators: dict) -> dict[str, Any]:
    rows = sorted(indicators.get("series") or [], key=lambda r: r.get("period_key") or "")
    emissions_labels: list[str] = []
    emissions_values: list[float] = []
    production_labels: list[str] = []
    production_values: list[float] = []
    intensity_labels: list[str] = []
    intensity_values: list[float] = []

    for row in rows:
        label = str(row.get("period_label") or row.get("period_key") or "")
        co2e_kg = num(row.get("co2e_kg"))
        milk = num(row.get("milk_liters"))
        intensity = bucket_intensity(row)
        if co2e_kg is not None:
            emissions_labels.append(label)
            emissions_values.append(round(co2e_kg / 1000, 4))
        if milk is not None:
            production_labels.append(label)
            production_values.append(milk)
        if intensity is not None:
            intensity_labels.append(label)
            intensity_values.append(round(intensity, 6))

    return {
        "emissions": {"labels": emissions_labels, "values": emissions_values, "unit": "t CO₂e"},
        "production": {"labels": production_labels, "values": production_values, "unit": "L"},
        "intensity": {"labels": intensity_labels, "values": intensity_values, "unit": "kg CO₂e/L"},
        "point_count": len(rows),
    }


def executive_temporal_governance_subtitle(meta: dict) -> str | None:
    hints: list[str] = []
    data_mode = meta.get("data_mode")
    if data_mode == "include_preliminary":
        if meta.get("has_preliminary_data"):
            hints.append("Dados preliminares — aguardando aprovação.")
        elif not meta.get("has_official_data"):
            hints.append("Dados preliminares — aguardando aprovação.")
    elif data_mode == "official_only":
        hints.append("Apenas ciclos aprovados/publicados.")
    agg = meta.get("aggregated_approval_status")
    if agg in ("partial_pending", "partial", "pending_approval"):
        hints.append("Inclui ciclos ainda não publicados.")
    if not hints:
        return None
    return " ".join(dict.fromkeys(hints))


def build_executive_temporal_section(indicators: dict, *, title: str = "Evolução temporal dos indicadores"):
    from dash import html

    from components.cards import SectionHeader
    from components.charts import ExecutiveTemporalChart, temporal_chart_empty_card
    from layout.theme import COLORS

    series = build_executive_temporal_series(indicators)
    meta = indicators.get("meta") or {}
    subtitle = executive_temporal_governance_subtitle(meta)

    chart_specs = [
        ("Emissões ao longo do tempo", series["emissions"], "t CO₂e",
         "Não há dados de emissões para o período selecionado.", COLORS["danger"],
         "<b>%{y:.2f} t CO₂e</b><extra></extra>", "ga-temporal-emissions-chart"),
        ("Produção ao longo do tempo", series["production"], "Litros de leite (L)",
         "Não há dados de produção para o período selecionado.", COLORS["primary"],
         "<b>%{y:,.0f} L</b><extra></extra>", "ga-temporal-production-chart"),
        ("Intensidade de emissão ao longo do tempo", series["intensity"], "kg CO₂e/L",
         "Não há dados suficientes para calcular intensidade.", COLORS["warning"],
         "<b>%{y:.3f} kg CO₂e/L</b><extra></extra>", "ga-temporal-intensity-chart"),
    ]

    cards: list = []
    for chart_title, metric, yaxis, empty_msg, color, hover, element_id in chart_specs:
        labels = metric.get("labels") or []
        values = metric.get("values") or []
        chart = ExecutiveTemporalChart(
            chart_title, labels, values, yaxis_title=yaxis, color=color,
            hover_template=hover, element_id=element_id,
        )
        body = chart if chart is not None else temporal_chart_empty_card(empty_msg)
        cards.append(html.Div(body, className="summary-card executive-temporal-slot mb-3 p-2"))

    return html.Div([
        SectionHeader(title, subtitle=subtitle),
        html.Div(cards, className="executive-temporal-section"),
    ], className="executive-temporal-block mb-3")


def build_dashboard_chart_components(
    charts: dict,
    *,
    for_executive: bool = False,
    for_general_analysis: bool = False,
):
    from components.charts import (
        BarChart,
        EmissionChart,
        ExecutiveEmissionSourcePieChart,
        GroupedBarChart,
        HorizontalBarChart,
        TemporalLineChart,
    )

    prod_ch = charts.get("productivity") or {}
    em_ch = charts.get("emissions") or {}
    sus_ch = charts.get("sustainability") or {}
    mgmt_ch = charts.get("management") or {}
    biz_ch = charts.get("business") or {}
    qual_ch = charts.get("data_quality") or {}
    pipe_ch = charts.get("pipeline") or {}
    aud_ch = charts.get("auditability") or {}

    mp = prod_ch.get("milk_by_period") or {}
    prod_charts = []
    if not for_executive:
        milk_line = TemporalLineChart(
            "Produção de leite por período", mp.get("labels", []), mp.get("values", []), "L",
        )
        if milk_line:
            prod_charts.append(milk_line)
        op_day = prod_ch.get("operational_milk_by_day") or {}
        op_line = TemporalLineChart(
            "Produção diária (operacional)", op_day.get("labels", []), op_day.get("values", []), "L",
        )
        if op_line:
            prod_charts.append(op_line)
    if not for_executive:
        if prod_ch.get("show_by_property"):
            mb = prod_ch.get("milk_by_property") or {}
            prod_charts.append(BarChart("Produção por propriedade", mb.get("labels", []), mb.get("values", [])))
        qual = prod_ch.get("quality") or {}
        if any(v is not None for v in qual.get("values") or []):
            prod_charts.append(BarChart("Composição do leite (%)", qual.get("labels", []), qual.get("values", []), yaxis_title="%"))

    co2e_p = em_ch.get("co2e_by_period_t") if for_general_analysis else em_ch.get("co2e_by_period") or {}
    int_p = em_ch.get("intensity_by_period") or {}
    comp = em_ch.get("period_comparison") or {}
    em_charts = []
    if not for_executive:
        yaxis = "t CO₂e" if for_general_analysis else "kg CO₂e"
        co2e_line = TemporalLineChart(
            "Emissões totais por período", co2e_p.get("labels", []), co2e_p.get("values", []), yaxis,
        )
        if co2e_line:
            em_charts.append(co2e_line)
        int_line = TemporalLineChart(
            "Intensidade por período", int_p.get("labels", []), int_p.get("values", []), "kg CO₂e/L",
        )
        if int_line:
            em_charts.append(int_line)
    if for_executive:
        em_charts.append(ExecutiveEmissionSourcePieChart(em_ch.get("by_source")))
    elif for_general_analysis:
        by_src = em_ch.get("by_source") or {}
        hbar = HorizontalBarChart(
            "Ranking de fontes emissoras", list(by_src.keys()), list(by_src.values()),
            xaxis_title="kg CO₂e",
        )
        if hbar:
            em_charts.append(hbar)
        gas = em_ch.get("by_gas") or {}
        if gas:
            em_charts.append(BarChart("Emissões por gás", list(gas.keys()), list(gas.values()), yaxis_title="kg CO₂e"))
    else:
        em_charts.extend([
            EmissionChart(em_ch.get("by_source"), chart_type="bar"),
            BarChart("Emissões por gás", list((em_ch.get("by_gas") or {}).keys()), list((em_ch.get("by_gas") or {}).values())),
        ])
    if not for_executive and comp.get("categories") and comp.get("current"):
        em_charts.append(GroupedBarChart(
            "Primeiro vs último período",
            comp.get("categories") or [],
            {"Último": comp.get("current") or [], "Primeiro": comp.get("previous") or []},
        ))

    cp = sus_ch.get("carbon_productivity") or {}
    sus_charts = []
    if not for_executive:
        cp_line = TemporalLineChart("Litros de leite por kg CO₂e", cp.get("labels", []), cp.get("values", []))
        if cp_line:
            sus_charts.append(cp_line)
        int_sus = sus_ch.get("intensity") or {}
        int_sus_line = TemporalLineChart("kg CO₂e por litro", int_sus.get("labels", []), int_sus.get("values", []), "kg CO₂e/L")
        if int_sus_line:
            sus_charts.append(int_sus_line)

    mgmt_charts = []
    feed5 = mgmt_ch.get("feed_top5") or {}
    if feed5.get("values"):
        mgmt_charts.append(BarChart("Top 5 insumos alimentares (kg)", feed5.get("labels", []), feed5.get("values", [])))
    fert = mgmt_ch.get("fertilizer_split") or {}
    if any(v is not None for v in fert.get("values") or []):
        mgmt_charts.append(BarChart("Fertilizantes (kg)", fert.get("labels", []), [v or 0 for v in fert.get("values", [])]))
    energy = mgmt_ch.get("energy_split") or {}
    if any(v is not None for v in energy.get("values") or []):
        mgmt_charts.append(BarChart("Consumo energético (kWh)", energy.get("labels", []), [v or 0 for v in energy.get("values", [])]))

    biz_charts = []
    pipe_sum = biz_ch.get("pipeline_summary") or {}
    if any(v is not None for v in pipe_sum.get("values") or []):
        biz_charts.append(BarChart("Resumo de ciclos", pipe_sum.get("labels", []), [v or 0 for v in pipe_sum.get("values", [])]))

    rb = qual_ch.get("record_breakdown") or {}
    qual_charts = []
    if rb:
        qual_charts.append(BarChart("Registros: válidos, alertas e erros", list(rb.keys()), list(rb.values())))
    err_step = qual_ch.get("errors_by_step") or {}
    if err_step:
        qual_charts.append(BarChart("Erros por etapa", list(err_step.keys()), list(err_step.values())))
    ct = qual_ch.get("completeness_trend") or {}
    ct_line = TemporalLineChart("Taxa de completude (%)", ct.get("labels", []), ct.get("values", []), yaxis_title="%")
    if ct_line:
        qual_charts.append(ct_line)

    pipe_charts = [
        BarChart("Ciclos por status", list((pipe_ch.get("cycles_by_status") or {}).keys()),
                 list((pipe_ch.get("cycles_by_status") or {}).values())),
        BarChart("Ciclos por etapa", list((pipe_ch.get("cycles_by_step") or {}).keys()),
                 list((pipe_ch.get("cycles_by_step") or {}).values())),
    ]

    aud_charts = [
        BarChart("Pacotes por status", list((aud_ch.get("packages_by_status") or {}).keys()),
                 list((aud_ch.get("packages_by_status") or {}).values())),
        BarChart("Verificações", list((aud_ch.get("verification_split") or {}).keys()),
                 list((aud_ch.get("verification_split") or {}).values())),
    ]

    return {
        "productivity": prod_charts,
        "emissions": em_charts,
        "sustainability": sus_charts,
        "management": mgmt_charts,
        "business": biz_charts,
        "data_quality": qual_charts,
        "pipeline": pipe_charts,
        "auditability": aud_charts,
    }
