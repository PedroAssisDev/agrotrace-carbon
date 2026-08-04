"""Montagem de seções da tela Análise Geral."""

from __future__ import annotations

from typing import Any

from services.indicator_kpi_service import build_section_kpis


def filter_nonempty_kpis(kpis: list[dict]) -> list[dict]:
    return [
        k for k in kpis
        if k.get("value") not in ("—", "N/A", None, "", "não disponível")
    ]


def build_overview_kpis(indicators: dict) -> list[dict]:
    prod = indicators.get("productivity") or {}
    return build_section_kpis(
        indicators, "overview",
        include_traceability=True,
        productivity_section=prod,
    )


def build_production_management_kpis(indicators: dict) -> list[dict]:
    prod = indicators.get("productivity") or {}
    return filter_nonempty_kpis(build_section_kpis(
        indicators, "production_management",
        include_traceability=False,
        productivity_section=prod,
    ))


def build_governance_kpis(indicators: dict) -> list[dict]:
    pipe = indicators.get("pipeline") or {}
    audit = indicators.get("auditability") or {}
    merged = {**pipe, **audit}
    fake = {**indicators, "governance": merged}
    return filter_nonempty_kpis(build_section_kpis(fake, "governance"))


def context_message(meta: dict) -> str | None:
    data_mode = meta.get("data_mode")
    if data_mode == "official_only":
        return "Esta análise considera apenas ciclos aprovados/publicados."
    if meta.get("includes_preliminary") or data_mode == "include_preliminary":
        return "Esta análise inclui resultados preliminares ainda não oficiais."
    if data_mode == "all":
        return "Esta análise inclui todos os ciclos disponíveis no período (preliminares e oficiais)."
    return None
