"""KPIs, insights e tabelas de apoio para indicadores gerenciais."""

from __future__ import annotations

from typing import Any

from utils.formatting import NA as _NA


def fmt_kpi_val(val, *, co2e: bool = False, intensity: bool = False, co2e_t: bool = False, liters: bool = False) -> str:
    from utils.formatting import format_co2e, format_co2e_t, format_intensity, format_liters, format_number

    if val is None or val == _NA:
        return _NA
    if co2e_t:
        return format_co2e_t(val)
    if co2e:
        return format_co2e(val)
    if intensity:
        return format_intensity(val)
    if liters:
        return format_liters(val)
    if isinstance(val, float):
        return format_number(val)
    return str(val)


def pct_display(val) -> str:
    if val is None or val == _NA:
        return _NA
    return f"{val}%"


KPI_SPECS: dict[str, list[tuple[str, str, str, str, bool, bool, bool, bool]]] = {
    "summary": [
        ("Produção total", "total_milk_liters", "fas fa-tint", "success", False, False, True, False),
        ("Emissões totais", "co2e_total_t", "fas fa-cloud", "danger", False, False, False, True),
        ("Intensidade", "intensity_consolidated_kg_per_l", "fas fa-chart-line", "primary", False, True, False, False),
        ("Principal fonte", "main_source", "fas fa-fire", "danger", False, False, False, False),
        ("Status do período", "period_status_label", "fas fa-info-circle", "info", False, False, False, False),
        ("Qualidade dos dados", "data_utilization_pct", "fas fa-database", "secondary", False, False, False, False),
        ("Aguard. aprovação", "awaiting_approval", "fas fa-user-clock", "warning", False, False, False, False),
        ("Eventos proveniência", "provenance_events", "fas fa-history", "info", False, False, False, False),
        ("Blockchain", "blockchain_status", "fas fa-link", "primary", False, False, False, False),
    ],
    "overview": [
        ("Produção total", "total_milk_liters", "fas fa-tint", "success", False, False, True, False),
        ("Emissões totais", "co2e_total_t", "fas fa-cloud", "danger", False, False, False, True),
        ("Intensidade", "intensity_consolidated_kg_per_l", "fas fa-chart-line", "primary", False, True, False, False),
        ("Principal fonte", "main_source", "fas fa-fire", "danger", False, False, False, False),
        ("Status do período", "period_status_label", "fas fa-info-circle", "info", False, False, False, False),
        ("Qualidade dos dados", "data_utilization_pct", "fas fa-database", "secondary", False, False, False, False),
        ("Aguard. aprovação", "awaiting_approval", "fas fa-user-clock", "warning", False, False, False, False),
        ("Eventos proveniência", "provenance_events", "fas fa-history", "info", False, False, False, False),
        ("Blockchain", "blockchain_status", "fas fa-link", "primary", False, False, False, False),
    ],
    "productivity": [
        ("Produção total", "total_milk_liters", "fas fa-tint", "success", False, False, True, False),
        ("Média diária", "avg_daily_liters", "fas fa-calendar-day", "info", False, False, True, False),
        ("Média mensal", "avg_monthly_liters", "fas fa-calendar", "info", False, False, True, False),
        ("Produção/animal", "milk_per_animal", "fas fa-paw", "success", False, False, True, False),
        ("Rebanho (média)", "total_animals", "fas fa-paw", "secondary", False, False, False, False),
        ("L/vaca lactação", "liters_per_lactating_cow", "fas fa-tint", "primary", False, False, True, False),
        ("Variação produção", "milk_variation_pct", "fas fa-chart-line", "warning", False, False, False, False),
        ("Melhor período", "best_period", "fas fa-arrow-up", "success", False, False, False, False),
        ("Pior período", "worst_period", "fas fa-arrow-down", "danger", False, False, False, False),
        ("Gordura do leite", "milk_fat_pct", "fas fa-percent", "info", False, False, False, False),
        ("Proteína do leite", "milk_protein_pct", "fas fa-percent", "info", False, False, False, False),
        ("Leite comercializado", "milk_sales_liters", "fas fa-shopping-cart", "success", False, False, True, False),
        ("Taxa comercialização", "sales_rate_pct", "fas fa-percent", "warning", False, False, False, False),
        ("Produção/ha", "liters_per_hectare", "fas fa-map", "primary", False, False, True, False),
    ],
    "production_management": [
        ("Produção total", "total_milk_liters", "fas fa-tint", "success", False, False, True, False),
        ("Média diária", "avg_daily_liters", "fas fa-calendar-day", "info", False, False, True, False),
        ("Média mensal", "avg_monthly_liters", "fas fa-calendar", "info", False, False, True, False),
        ("Produção/animal", "milk_per_animal", "fas fa-paw", "success", False, False, True, False),
        ("Rebanho (média)", "total_animals", "fas fa-paw", "secondary", False, False, False, False),
        ("Produção/ha", "liters_per_hectare", "fas fa-map", "primary", False, False, True, False),
        ("Área pastagem (ha)", "pasture_area_ha", "fas fa-map-marked-alt", "success", False, False, False, False),
        ("Insumo alimentar (kg)", "total_feed_input_kg", "fas fa-wheat-awn", "secondary", False, False, False, False),
        ("Fert. orgânico (kg)", "organic_fertilizer_kg", "fas fa-seedling", "success", False, False, False, False),
        ("Energia rede (kWh)", "electricity_grid_kwh", "fas fa-plug", "secondary", False, False, False, False),
        ("Energia solar (kWh)", "photovoltaic_energy_kwh", "fas fa-solar-panel", "warning", False, False, False, False),
        ("Efic. alimentar (L/kg)", "feed_efficiency", "fas fa-balance-scale", "info", False, False, False, False),
    ],
    "management": [
        ("Área pastagem (ha)", "pasture_area_ha", "fas fa-map-marked-alt", "success", False, False, False, False),
        ("Área leiteira (ha)", "dairy_area_ha", "fas fa-map", "info", False, False, False, False),
        ("Insumo alimentar (kg)", "total_feed_input_kg", "fas fa-wheat-awn", "secondary", False, False, False, False),
        ("MS ingerida (kg/dia)", "dry_matter_intake", "fas fa-weight", "info", False, False, False, False),
        ("Densidade energética", "energy_density", "fas fa-bolt", "warning", False, False, False, False),
        ("Fert. orgânico (kg)", "organic_fertilizer_kg", "fas fa-seedling", "success", False, False, False, False),
        ("Fert. químico (kg)", "non_organic_fertilizer_kg", "fas fa-flask", "danger", False, False, False, False),
        ("Fert. orgânico (%)", "organic_fertilizer_pct", "fas fa-leaf", "success", False, False, False, False),
        ("Energia rede (kWh)", "electricity_grid_kwh", "fas fa-plug", "secondary", False, False, False, False),
        ("Energia solar (kWh)", "photovoltaic_energy_kwh", "fas fa-solar-panel", "warning", False, False, False, False),
        ("Energia renovável (%)", "renewable_energy_pct", "fas fa-sun", "success", False, False, False, False),
        ("Densidade animal (UA/ha)", "animals_per_hectare", "fas fa-paw", "primary", False, False, False, False),
        ("Efic. alimentar (L/kg)", "feed_efficiency", "fas fa-balance-scale", "info", False, False, False, False),
    ],
    "business": [
        ("Preço bruto leite", "milk_gross_price", "fas fa-dollar-sign", "success", False, False, False, False),
        ("Receita bruta est.", "estimated_gross_revenue", "fas fa-coins", "primary", False, False, False, False),
        ("Funcionários", "employees_count", "fas fa-users", "info", False, False, False, False),
        ("Produção/funcionário", "milk_per_employee", "fas fa-user-check", "success", False, False, True, False),
        ("Ciclos em andamento", "cycles_in_progress", "fas fa-sync", "info", False, False, False, False),
        ("Aguard. aprovação", "awaiting_approval", "fas fa-user-clock", "warning", False, False, False, False),
        ("Ciclos aprovados", "cycles_approved", "fas fa-check", "success", False, False, False, False),
        ("Aproveitamento dados", "data_utilization_pct", "fas fa-database", "secondary", False, False, False, False),
        ("Alertas semânticos", "semantic_warnings", "fas fa-bell", "warning", False, False, False, False),
    ],
    "emissions": [
        ("CO₂e total", "co2e_total_t", "fas fa-cloud", "danger", False, False, False, True),
        ("Intensidade", "intensity_consolidated_kg_per_l", "fas fa-tint", "primary", False, True, False, False),
        ("CO₂e/animal", "co2e_per_animal", "fas fa-paw", "warning", True, False, False, False),
        ("CH₄ total", "ch4_total_kg", "fas fa-wind", "info", True, False, False, False),
        ("N₂O total", "n2o_total_kg", "fas fa-seedling", "warning", True, False, False, False),
        ("CO₂ energia", "co2_total_kg", "fas fa-bolt", "secondary", True, False, False, False),
        ("Principal fonte", "main_source", "fas fa-fire", "danger", False, False, False, False),
        ("Participação principal", "main_source_pct", "fas fa-percent", "danger", False, False, False, False),
        ("Variação emissões", "co2e_variation_pct", "fas fa-percent", "warning", False, False, False, False),
    ],
    "sustainability": [
        ("L/kg CO₂e", "liters_per_kg_co2e", "fas fa-leaf", "success", False, False, False, False),
        ("kg CO₂e/L", "kg_co2e_per_liter", "fas fa-tint", "primary", False, True, False, False),
        ("Emissões biogênicas", "biogenic_pct", "fas fa-tree", "success", False, False, False, False),
        ("Emissões energéticas", "energy_pct", "fas fa-bolt", "secondary", False, False, False, False),
        ("CO₂e/ha", "co2e_per_hectare", "fas fa-cloud", "danger", True, False, False, False),
    ],
    "data_quality": [
        ("Arquivos brutos", "raw_files", "fas fa-file", "secondary", False, False, False, False),
        ("Registros normalizados", "normalized_records", "fas fa-database", "info", False, False, False, False),
        ("Registros válidos", "valid_records", "fas fa-check-circle", "success", False, False, False, False),
        ("Com alerta", "alert_records", "fas fa-exclamation", "warning", False, False, False, False),
        ("Com erro", "error_records", "fas fa-times-circle", "danger", False, False, False, False),
        ("Aproveitamento", "utilization_pct", "fas fa-percent", "success", False, False, False, False),
        ("Rejeição wrapper", "rejection_pct", "fas fa-ban", "danger", False, False, False, False),
        ("Erros semânticos", "semantic_errors", "fas fa-bug", "danger", False, False, False, False),
        ("Alertas semânticos", "semantic_warnings", "fas fa-bell", "warning", False, False, False, False),
        ("Períodos incompletos", "incomplete_periods", "fas fa-exclamation-triangle", "warning", False, False, False, False),
    ],
    "pipeline": [
        ("Total de ciclos", "total_cycles", "fas fa-list", "secondary", False, False, False, False),
        ("Em andamento", "in_progress", "fas fa-sync", "info", False, False, False, False),
        ("Aguard. aprovação", "awaiting_approval", "fas fa-user-clock", "warning", False, False, False, False),
        ("Aprovados", "approved", "fas fa-check", "success", False, False, False, False),
        ("Rejeitados", "rejected", "fas fa-times", "danger", False, False, False, False),
        ("Publicados", "published", "fas fa-book", "primary", False, False, False, False),
        ("Progresso médio", "avg_progress_pct", "fas fa-tasks", "info", False, False, False, False),
        ("Última etapa", "last_step", "fas fa-shoe-prints", "secondary", False, False, False, False),
        ("Etapa c/ mais falhas", "most_failed_step", "fas fa-exclamation-triangle", "danger", False, False, False, False),
    ],
    "auditability": [
        ("Eventos proveniência", "provenance_events", "fas fa-history", "info", False, False, False, False),
        ("Pacotes evidência", "evidence_packages", "fas fa-box", "primary", False, False, False, False),
        ("Hashes gerados", "hashes_generated", "fas fa-fingerprint", "secondary", False, False, False, False),
        ("Merkle roots", "merkle_roots", "fas fa-project-diagram", "info", False, False, False, False),
        ("Ancorados", "anchored_packages", "fas fa-link", "success", False, False, False, False),
        ("Verificações", "verifications_run", "fas fa-shield-alt", "primary", False, False, False, False),
        ("Íntegras", "verifications_ok", "fas fa-check-double", "success", False, False, False, False),
        ("Divergentes", "verifications_divergent", "fas fa-exclamation-triangle", "danger", False, False, False, False),
        ("Integridade geral", "integrity_status", "fas fa-lock", "success", False, False, False, False),
    ],
    "governance": [
        ("Ciclos em andamento", "in_progress", "fas fa-sync", "info", False, False, False, False),
        ("Aguard. aprovação", "awaiting_approval", "fas fa-user-clock", "warning", False, False, False, False),
        ("Aprovados", "approved", "fas fa-check", "success", False, False, False, False),
        ("Publicados", "published", "fas fa-book", "primary", False, False, False, False),
        ("Eventos proveniência", "provenance_events", "fas fa-history", "info", False, False, False, False),
        ("Pacotes evidência", "evidence_packages", "fas fa-box", "primary", False, False, False, False),
        ("Ancorados", "anchored_packages", "fas fa-link", "success", False, False, False, False),
        ("Integridade geral", "integrity_status", "fas fa-lock", "success", False, False, False, False),
    ],
}

PCT_KEYS = frozenset({
    "milk_variation_pct", "co2e_variation_pct", "biogenic_pct", "energy_pct",
    "utilization_pct", "rejection_pct", "avg_progress_pct",
    "sales_rate_pct", "organic_fertilizer_pct", "renewable_energy_pct",
    "data_utilization_pct", "main_source_pct",
})
TRUNC_KEYS = frozenset({"main_source", "last_step", "most_failed_step", "period_status_label", "blockchain_status"})

SEVERITY_GROUPS = {
    "critical": "Crítico",
    "warning": "Atenção",
    "info": "Informativo",
    "success": "Positivo",
}


def build_traceability_subtitle(meta: dict) -> str:
    parts = []
    count = meta.get("cycle_count", 0)
    if count:
        parts.append(f"{count} ciclo(s)")
    if meta.get("includes_preliminary"):
        parts.append("inclui preliminares")
    mode = meta.get("integration_mode")
    if mode == "real":
        parts.append("dados reais")
    elif mode == "mock":
        parts.append("dados simulados")
    elif mode == "mixed":
        parts.append("dados mistos")
    period = meta.get("period_label")
    if period:
        parts.append(str(period))
    return " · ".join(parts) if parts else ""


def build_section_kpis(
    indicators: dict,
    section_key: str,
    *,
    include_traceability: bool = False,
    productivity_section: dict | None = None,
) -> list[dict]:
    section = indicators.get(section_key) or {}
    if section_key in ("overview", "summary"):
        section = {**(indicators.get("summary") or {}), **section}
    if section_key == "production_management":
        prod = indicators.get("productivity") or {}
        mgmt = indicators.get("management") or {}
        section = {**prod, **mgmt}
    specs = KPI_SPECS.get(section_key, [])
    meta = indicators.get("meta") or {}
    trace_sub = build_traceability_subtitle(meta) if include_traceability else ""
    kpis = []
    for title, key, icon, color, co2e, intensity, liters, co2e_t in specs:
        val = section.get(key)
        if key in PCT_KEYS:
            display = pct_display(val)
        elif key in TRUNC_KEYS and val not in (None, _NA):
            display = str(val)[:28] if key == "main_source" else str(val)[:24]
        elif isinstance(val, int):
            display = str(val)
        else:
            display = fmt_kpi_val(val, co2e=co2e, intensity=intensity, liters=liters, co2e_t=co2e_t)
        subtitle = trace_sub if include_traceability and key in (
            "total_milk_liters", "co2e_total_t", "intensity_consolidated_kg_per_l", "main_source",
        ) else ""
        if key == "avg_daily_liters" and productivity_section:
            note = productivity_section.get("avg_daily_note")
            if note:
                subtitle = note
        if key == "total_animals" and productivity_section:
            mode = productivity_section.get("total_animals_mode")
            if mode == "avg_period":
                subtitle = "Média do rebanho no período"
        kpis.append({"title": title, "value": display, "icon": icon, "color": color, "subtitle": subtitle})
    return kpis


def generate_dashboard_insights(indicators: dict) -> list[dict]:
    insights: list[dict] = []
    em = indicators.get("emissions") or {}
    prod = indicators.get("productivity") or {}
    sus = indicators.get("sustainability") or {}
    mgmt = indicators.get("management") or {}
    qual = indicators.get("data_quality") or {}
    pipe = indicators.get("pipeline") or {}
    audit = indicators.get("auditability") or {}
    meta = indicators.get("meta") or {}

    main = em.get("main_source")
    if main and main != _NA:
        pct = em.get("main_source_pct")
        msg = f"{main} é a principal fonte de emissões no período."
        if isinstance(pct, (int, float)):
            msg += f" Participação: {pct:.1f}%."
        insights.append({"type": "emissao", "severity": "info", "title": "Principal fonte emissora", "message": msg})

    iv = em.get("intensity_variation_pct")
    if isinstance(iv, (int, float)):
        sev = "warning" if iv > 0 else "success"
        dir_ = "aumentou" if iv > 0 else "diminuiu"
        insights.append({
            "type": "emissao", "severity": sev, "title": "Tendência de intensidade",
            "message": f"A intensidade kg CO₂e/L {dir_} {abs(iv):.1f}% do início ao fim do período filtrado.",
        })

    ev = em.get("co2e_variation_pct")
    if isinstance(ev, (int, float)):
        sev = "warning" if ev > 0 else "success"
        dir_ = "aumentaram" if ev > 0 else "diminuíram"
        insights.append({
            "type": "emissao", "severity": sev, "title": "Tendência de emissões",
            "message": f"As emissões {dir_} {abs(ev):.1f}% do início ao fim do período filtrado.",
        })

    mv = prod.get("milk_variation_pct")
    if isinstance(mv, (int, float)) and mv > 5:
        insights.append({
            "type": "produtividade", "severity": "success", "title": "Tendência de produção",
            "message": f"A produção de leite cresceu {mv:.1f}% do início ao fim do período filtrado.",
        })
    elif isinstance(mv, (int, float)) and mv < -5:
        insights.append({
            "type": "produtividade", "severity": "warning", "title": "Queda de produção",
            "message": f"A produção de leite caiu {abs(mv):.1f}% do início ao fim do período filtrado.",
        })

    if isinstance(mv, (int, float)) and isinstance(ev, (int, float)) and mv > 0 and ev > mv:
        insights.append({
            "type": "produtividade", "severity": "warning", "title": "Produção vs emissões",
            "message": "A produção aumentou, mas as emissões cresceram proporcionalmente mais.",
        })

    if meta.get("blockchain_blocked"):
        insights.append({
            "type": "blockchain", "severity": "info", "title": "Blockchain bloqueado",
            "message": "Blockchain bloqueado até publicação final da ontologia aprovada.",
        })

    if (qual.get("alert_records") or 0) > 0 or (qual.get("semantic_warnings") or 0) > 0:
        insights.append({
            "type": "qualidade", "severity": "warning", "title": "Alerta de qualidade dos dados",
            "message": "Há registros com alerta que podem afetar a confiabilidade do cálculo.",
        })

    if (pipe.get("awaiting_approval") or 0) > 0:
        insights.append({
            "type": "pipeline", "severity": "warning", "title": "Pendência de aprovação",
            "message": f"{pipe['awaiting_approval']} ciclo(s) aguardam aprovação humana.",
        })

    if (audit.get("verifications_divergent") or 0) > 0:
        insights.append({
            "type": "auditoria", "severity": "critical", "title": "Divergência de integridade",
            "message": "Foram encontradas divergências na verificação de integridade.",
        })

    best = prod.get("best_period")
    worst = prod.get("worst_period")
    if best and best != _NA and worst and worst != _NA and best != worst:
        insights.append({
            "type": "produtividade", "severity": "info", "title": "Foco gerencial",
            "message": f"Melhor período: {best}. Pior período: {worst}.",
        })

    perf = sus.get("environmental_performance")
    trend = sus.get("environmental_trend")
    if perf and perf != _NA:
        insights.append({
            "type": "emissao",
            "severity": "success" if perf == "bom" else ("critical" if perf == "crítico" else "warning"),
            "title": "Desempenho ambiental",
            "message": f"Classificação: {perf} (tendência: {trend}). Quanto menor kg CO₂e/L, melhor.",
        })

    renew = mgmt.get("renewable_energy_pct")
    if isinstance(renew, (int, float)) and renew >= 10:
        insights.append({
            "type": "manejo", "severity": "success", "title": "Energia renovável",
            "message": f"{renew:.1f}% do consumo elétrico provém de fonte fotovoltaica.",
        })

    return insights


def group_insights_by_severity(insights: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {k: [] for k in SEVERITY_GROUPS}
    for ins in insights:
        sev = ins.get("severity", "info")
        groups.setdefault(sev, []).append(ins)
    return groups


def build_dashboard_tables(indicators: dict) -> dict:
    series = indicators.get("series") or []
    em = indicators.get("emissions") or {}
    insights = generate_dashboard_insights(indicators)
    audit = indicators.get("auditability") or {}
    qual = indicators.get("data_quality") or {}

    period_rows = []
    for r in series:
        integrity = r.get("integrity")
        if integrity is True:
            integ_label = "íntegro"
        elif integrity is False:
            integ_label = "divergente"
        else:
            integ_label = str(integrity) if integrity else "—"
        period_rows.append({
            "Período": r.get("period_label") or r.get("period"),
            "Produção (L)": r.get("milk_liters") if r.get("milk_liters") is not None else _NA,
            "Emissões (t CO₂e)": round(r["co2e_kg"] / 1000, 2) if r.get("co2e_kg") is not None else _NA,
            "kg CO₂e/L": r.get("intensity") if r.get("intensity") is not None else _NA,
            "Status do ciclo": r.get("status") or "—",
            "Integridade": integ_label,
        })

    alert_rows = []
    for ins in insights:
        alert_rows.append({
            "Tipo": ins.get("type", "—"),
            "Indicador": ins.get("title", "—"),
            "Mensagem": ins.get("message", "—"),
            "Severidade": SEVERITY_GROUPS.get(ins.get("severity", "info"), ins.get("severity", "info")),
            "Período": series[-1].get("period_label") if series else "—",
        })

    cycle_rows = []
    for r in series:
        cycle_rows.append({
            "Ciclo": r.get("cycle_id") or "—",
            "Período": r.get("period_label") or r.get("period") or "—",
            "Status": r.get("status") or "—",
            "Produção (L)": r.get("milk_liters") if r.get("milk_liters") is not None else _NA,
            "Emissões (t CO₂e)": round(r["co2e_kg"] / 1000, 2) if r.get("co2e_kg") is not None else _NA,
        })

    return {
        "ranking_sources": em.get("source_ranking") or [],
        "period_indicators": period_rows,
        "management_alerts": alert_rows,
        "recent_audit": alert_rows,
        "cycles_analyzed": cycle_rows,
        "traceability": qual.get("traceability_rows") or [],
        "integrity_status": audit.get("integrity_status"),
    }
