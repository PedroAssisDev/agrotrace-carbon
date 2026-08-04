"""Filtro global: escopo analítico (fazenda + período) e referência operacional (cycle_id).

Dois contextos (ver docs/conceptual_model_mrv.md):

- **Analítico:** ``cycles_for_analysis()`` — vários ciclos no período; alimenta KPIs/gráficos.
- **Operacional:** ``filter_cycles_by_context()`` — um ciclo; proveniência, evidências, wizard.

``cycle_id`` no store = ciclo operacional de referência (sinônimo conceitual: operational_cycle_id).
Não substitui ``analysis_period_start/end`` como driver exclusivo de dashboards.

Arquitetura de filtros: docs/filter_architecture_mrv.md
"""

from __future__ import annotations

import copy
import re
from typing import Any

from utils.property_filter import (
    aggregate_calculation_metrics,
    filter_by_farm,
    get_all_property_ids,
    get_selected_farm_label,
    normalize_property_id,
    resolve_active_cycle,
)

_PERIOD_RE = re.compile(r"^(\d{4})-(\d{2})$")
_YEAR_RE = re.compile(r"^(\d{4})$")
_YEAR_RANGE_RE = re.compile(r"^(\d{4})-(\d{4})$")
_DATE_RANGE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})/(\d{4}-\d{2}-\d{2})$")

MONTH_LABELS = {
    "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
    "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
    "09": "Set", "10": "Out", "11": "Nov", "12": "Dez",
}

GRANULARITY_LABELS = {
    "monthly": "Mensal",
    "annual": "Anual",
    "daily": "Diário",
    "current_cycle": "Ciclo atual",
}

VIEW_GRANULARITY_OPTIONS = {
    "auto": "Automático",
    "monthly": "Mensal",
    "quarterly": "Trimestral",
    "semester": "Semestral",
    "annual": "Anual",
    "consolidated": "Consolidado",
}

DATA_MODE_OPTIONS = {
    "official_only": "Oficial",
    "include_preliminary": "Incluir preliminares",
    "all": "Todos",
}

DEFAULT_GLOBAL_FILTER: dict[str, Any] = {
    "farm_id": None,
    "farm_name": None,
    "cycle_id": None,
    "period": None,
    "period_display_label": None,
    "granularity": None,
    "input_granularity": None,
    "calculation_base_granularity": None,
    "view_granularity": "auto",
    "data_mode": "include_preliminary",
    "analysis_period_start": None,
    "analysis_period_end": None,
    "cycle_status": None,
    "approval_status": None,
    "publication_status": None,
    "evidence_status": None,
}


def normalize_data_mode(value: str | None) -> str:
    if isinstance(value, str) and value.strip() in DATA_MODE_OPTIONS:
        return value.strip()
    return DEFAULT_GLOBAL_FILTER["data_mode"]


def normalize_view_granularity(value: str | None) -> str:
    if isinstance(value, str) and value.strip() in VIEW_GRANULARITY_OPTIONS:
        return value.strip()
    return DEFAULT_GLOBAL_FILTER["view_granularity"]


def filter_cycles_by_data_mode(cycles: list[dict], data_mode: str | None) -> list[dict]:
    """Filtra ciclos para KPIs/gráficos conforme governança de dados."""
    from services.cycle_status_service import resolve_managerial_status

    mode = normalize_data_mode(data_mode)
    if mode == "all":
        return list(cycles)
    if mode == "include_preliminary":
        return list(cycles)
    return [c for c in cycles if resolve_managerial_status(c).is_official]


def get_farm_id(filters: dict[str, Any] | None) -> str | None:
    """Extrai farm_id do filtro global (compatível com sessões antigas com property_ids)."""
    if not filters:
        return None
    farm_id = filters.get("farm_id")
    if isinstance(farm_id, str) and farm_id.strip():
        return farm_id.strip()
    legacy = filters.get("property_ids")
    if isinstance(legacy, list) and legacy:
        first = legacy[0]
        return first if isinstance(first, str) and first.strip() else None
    return None


def is_no_farm_selected(filters: dict[str, Any] | None) -> bool:
    return not get_farm_id(filters)


def _farm_name_from_id(farm_id: str | None) -> str | None:
    if not farm_id:
        return None
    from services.property_registry import load_property_catalog

    for p in load_property_catalog():
        if p.get("property_id") == farm_id:
            return p.get("name") or farm_id
    return farm_id


def derive_status_fields(cycle: dict | None) -> dict[str, Any]:
    """Deriva status técnico e gerencial a partir do ciclo ativo."""
    empty = {
        "cycle_status": None,
        "approval_status": None,
        "publication_status": None,
        "evidence_status": None,
    }
    if not cycle or not cycle.get("cycle_id"):
        return empty

    from services.cycle_status_service import resolve_managerial_status

    mgr = resolve_managerial_status(cycle)
    publication = cycle.get("publication") or {}
    pub_status = publication.get("status")
    if not pub_status:
        pub_step = (cycle.get("steps") or {}).get("publication") or {}
        pub_status = "Published" if pub_step.get("status") in {"DONE", "DONE_WARNINGS"} else "NotPublished"

    evidence_status = "NotGenerated"
    if cycle.get("evidence_package"):
        evidence_status = "Generated"
    if (cycle.get("integrity") or {}).get("is_valid") is True:
        evidence_status = "Verified"

    return {
        "cycle_status": cycle.get("current_status") or cycle.get("status"),
        "approval_status": mgr.key,
        "publication_status": pub_status,
        "evidence_status": evidence_status,
    }


def normalize_global_filter(filters: dict[str, Any] | None) -> dict[str, Any]:
    """Garante schema mínimo do filtro global (sem re-normalizar ciclo)."""
    base = copy.deepcopy(DEFAULT_GLOBAL_FILTER)
    if not filters:
        return base
    base["farm_id"] = get_farm_id(filters)
    cycle_id = filters.get("cycle_id")
    base["cycle_id"] = cycle_id if isinstance(cycle_id, str) and cycle_id.strip() else None
    for key in (
        "farm_name", "period", "period_display_label", "granularity", "cycle_status",
        "approval_status", "publication_status", "evidence_status",
        "input_granularity", "calculation_base_granularity", "view_granularity",
        "data_mode", "analysis_period_start", "analysis_period_end",
    ):
        if filters.get(key) is not None:
            base[key] = filters[key]
    return base


def cycle_belongs_to_farm(cycle: dict | None, farm_id: str | None) -> bool:
    if not cycle or not farm_id:
        return False
    pid = normalize_property_id(cycle)
    return pid == farm_id or farm_id in get_all_property_ids(cycle)


def cycles_for_farm(all_cycles: list[dict], farm_id: str | None) -> list[dict]:
    if not farm_id:
        return []
    return filter_by_farm(all_cycles, farm_id)


def cycles_for_analysis(
    all_cycles: list[dict],
    filters: dict[str, Any],
    active_cycle: dict | None = None,
) -> list[dict]:
    """Ciclos da fazenda no escopo **analítico** (KPIs, gráficos, tendências).

    Pode retornar vários ciclos dentro de ``analysis_period_start/end``.
    Distinto de ``filter_cycles_by_context()`` (escopo operacional, um ciclo).
    """
    candidates = analysis_scenario_cycles(all_cycles, filters, active_cycle)
    gf = filters or {}
    start = gf.get("analysis_period_start")
    end = gf.get("analysis_period_end")
    if not start and not end:
        return candidates
    return filter_cycles_by_analysis_period(candidates, start, end)


def analysis_scenario_cycles(
    all_cycles: list[dict],
    filters: dict[str, Any],
    active_cycle: dict | None = None,
) -> list[dict]:
    """Ciclos elegíveis para análise (mesmo cenário temporal), antes do filtro de período."""
    gf = normalize_global_filter(filters)
    farm_id = gf.get("farm_id")
    if not farm_id:
        return []
    farm = cycles_for_farm(all_cycles, farm_id)
    if not farm:
        return []

    ref = active_cycle
    if not ref or not ref.get("cycle_id"):
        ref = pick_default_cycle(farm, gf.get("cycle_id")) or (farm[0] if farm else None)
    if not ref:
        return sorted(farm, key=lambda c: c.get("reporting_period") or "")

    ref_kind = (ref.get("temporal_coverage") or {}).get("kind")
    if ref_kind:
        matched = [
            c for c in farm
            if (c.get("temporal_coverage") or {}).get("kind") == ref_kind
        ]
        if len(matched) > 1:
            return sorted(matched, key=lambda c: c.get("reporting_period") or "")

    return sorted(farm, key=lambda c: c.get("reporting_period") or "")


def period_sort_key(period: str | None) -> str:
    """Chave ordenável para comparação de períodos (anual, mensal, range)."""
    if not period:
        return ""
    period = period.strip()
    if _YEAR_RE.match(period):
        return f"{period}-01"
    if _PERIOD_RE.match(period):
        return period
    range_match = _YEAR_RANGE_RE.match(period)
    if range_match:
        return f"{range_match.group(1)}-01"
    date_match = _DATE_RANGE_RE.match(period)
    if date_match:
        return date_match.group(1)
    return period


def period_in_analysis_range(
    period: str | None,
    start: str | None,
    end: str | None,
) -> bool:
    if not period:
        return False
    if not start and not end:
        return True
    key = period_sort_key(period)
    if start and key < period_sort_key(start):
        return False
    if end and key > period_sort_key(end):
        return False
    return True


def filter_cycles_by_analysis_period(
    cycles: list[dict],
    start: str | None,
    end: str | None,
) -> list[dict]:
    if not start and not end:
        return list(cycles)
    return [
        c for c in cycles
        if period_in_analysis_range(cycle_period(c), start, end)
    ]


def resolve_analysis_period_bounds(
    candidates: list[dict],
    raw_start: str | None,
    raw_end: str | None,
) -> tuple[str | None, str | None]:
    """Resolve início/fim do período de análise (default = span completo dos ciclos)."""
    periods = sorted(
        {p for p in (cycle_period(c) for c in candidates) if p},
        key=period_sort_key,
    )
    if not periods:
        return None, None

    valid = set(periods)
    start = raw_start if isinstance(raw_start, str) and raw_start in valid else periods[0]
    end = raw_end if isinstance(raw_end, str) and raw_end in valid else periods[-1]
    if period_sort_key(start) > period_sort_key(end):
        start, end = end, start
    return start, end


def analysis_period_dropdown_options(candidates: list[dict]) -> list[dict[str, str]]:
    """Opções de período para os dropdowns de análise (início/fim)."""
    from utils.temporal_model import infer_input_granularity, resolve_calculation_base_granularity
    from utils.temporal_series import period_chart_label

    ref = candidates[0] if candidates else {}
    calc_base = resolve_calculation_base_granularity(infer_input_granularity(ref))
    seen: dict[str, str] = {}
    for c in sorted(candidates, key=lambda x: period_sort_key(cycle_period(x) or "")):
        period = cycle_period(c)
        if not period or period in seen:
            continue
        seen[period] = period_chart_label(
            period[:7] if calc_base == "monthly" and len(period) >= 7 else period,
            calc_base,
        )
    return [{"label": lbl, "value": key} for key, lbl in seen.items()]


def format_analysis_period_display(
    start: str | None,
    end: str | None,
    calc_base: str = "monthly",
) -> str:
    from utils.temporal_series import period_chart_label

    if not start and not end:
        return "—"
    if start and end and start == end:
        key = start[:7] if calc_base == "monthly" and len(start) >= 7 else start
        return period_chart_label(key, calc_base)
    if start and end:
        sk = start[:7] if calc_base == "monthly" and len(start) >= 7 else start
        ek = end[:7] if calc_base == "monthly" and len(end) >= 7 else end
        return f"{period_chart_label(sk, calc_base)} a {period_chart_label(ek, calc_base)}"
    key = (start or end) or ""
    return period_chart_label(
        key[:7] if calc_base == "monthly" and len(key) >= 7 else key,
        calc_base,
    )


def _derive_temporal_fields(
    analysis_cycles: list[dict],
    active_cycle: dict,
    raw_filters: dict[str, Any],
) -> dict[str, Any]:
    from utils.temporal_model import (
        build_analysis_period_display_label,
        build_temporal_model,
        infer_input_granularity,
        resolve_calculation_base_granularity,
    )

    input_gr = infer_input_granularity(active_cycle)
    calc_base = resolve_calculation_base_granularity(input_gr)
    view_gr = normalize_view_granularity(raw_filters.get("view_granularity"))
    data_mode = normalize_data_mode(raw_filters.get("data_mode"))
    filtered = filter_cycles_by_data_mode(analysis_cycles, data_mode)
    temporal = (
        build_temporal_model(filtered, active_cycle, view_gr, data_mode=data_mode)
        if filtered
        else None
    )

    return {
        "period_display_label": (
            build_analysis_period_display_label(analysis_cycles, calc_base)
            if analysis_cycles
            else (temporal.period_display_label if temporal else format_cycle_period_label(active_cycle))
        ),
        "granularity": calc_base,
        "input_granularity": input_gr,
        "calculation_base_granularity": calc_base,
        "view_granularity": view_gr,
        "data_mode": data_mode,
        "aggregated_approval_status": temporal.aggregated_approval_status if temporal else None,
    }


def cycle_period(cycle: dict | None) -> str | None:
    """Período canônico do ciclo (YYYY-MM, YYYY ou range diário)."""
    if not cycle:
        return None
    for key in ("reporting_period", "period"):
        val = cycle.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    raw = cycle.get("raw_file")
    if isinstance(raw, dict):
        for key in ("reporting_period", "period"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None


def cycle_granularity(cycle: dict | None) -> str:
    """Granularidade UI a partir do ciclo (intraday → daily)."""
    if not cycle:
        return "monthly"
    g = str(cycle.get("granularity") or "").lower()
    if g in ("annual",):
        return "annual"
    if g in ("intraday", "daily"):
        return "daily"
    layout = str((cycle.get("wrapper") or {}).get("layout_id") or "")
    if "annual" in layout:
        return "annual"
    if "intraday" in layout or "daily" in layout:
        return "daily"
    return "monthly"


def _cycle_sort_key(cycle: dict) -> str:
    return cycle.get("updated_at") or cycle.get("created_at") or ""


def pick_active_from_analysis(
    analysis_cycles: list[dict],
    *,
    preferred_cycle_id: str | None = None,
    period_end: str | None = None,
) -> dict:
    """Ciclo de referência operacional dentro do intervalo analítico."""
    if not analysis_cycles:
        return {}
    if preferred_cycle_id:
        for c in analysis_cycles:
            if c.get("cycle_id") == preferred_cycle_id:
                return c
    if period_end:
        for c in reversed(analysis_cycles):
            if cycle_period(c) == period_end:
                return c
    return analysis_cycles[-1]


def pick_default_cycle(
    farm_cycles: list[dict],
    preferred_cycle_id: str | None = None,
) -> dict | None:
    """Escolhe ciclo determinístico: preferido se válido, senão o mais recente."""
    if not farm_cycles:
        return None
    if preferred_cycle_id:
        for c in farm_cycles:
            if c.get("cycle_id") == preferred_cycle_id:
                return c
    return max(farm_cycles, key=_cycle_sort_key)


def _empty_context(farm_id: str | None = None, farm_name: str | None = None) -> dict[str, Any]:
    out = copy.deepcopy(DEFAULT_GLOBAL_FILTER)
    if farm_id:
        out["farm_id"] = farm_id
        out["farm_name"] = farm_name or _farm_name_from_id(farm_id)
    return out


def normalize_filter_state(
    raw_filters: dict[str, Any] | None,
    available_cycles: list[dict] | None = None,
    *,
    context_cycle_id: str | None = None,
) -> dict[str, Any]:
    """Normaliza estado global: fazenda → ciclo → período/granularidade/status derivados."""
    from utils.file_helpers import list_cycles

    all_cycles = available_cycles if available_cycles is not None else list_cycles()
    farm_id = get_farm_id(raw_filters)

    if not farm_id:
        return copy.deepcopy(DEFAULT_GLOBAL_FILTER)

    farm_name = _farm_name_from_id(farm_id)
    farm_cycles = cycles_for_farm(all_cycles, farm_id)
    if not farm_cycles:
        return _empty_context(farm_id, farm_name)

    preferred: str | None = None
    if raw_filters:
        cid = raw_filters.get("cycle_id")
        if isinstance(cid, str) and cid.strip():
            preferred = cid.strip()
    if not preferred and context_cycle_id:
        preferred = context_cycle_id

    raw_gf = raw_filters or {}
    scenario_ref = pick_default_cycle(farm_cycles, preferred) or (farm_cycles[0] if farm_cycles else None)
    if not scenario_ref:
        return _empty_context(farm_id, farm_name)

    candidates = analysis_scenario_cycles(
        all_cycles,
        {"farm_id": farm_id},
        scenario_ref,
    )
    period_start, period_end = resolve_analysis_period_bounds(
        candidates,
        raw_gf.get("analysis_period_start"),
        raw_gf.get("analysis_period_end"),
    )
    analysis_cycles = filter_cycles_by_analysis_period(candidates, period_start, period_end)
    active = pick_active_from_analysis(
        analysis_cycles,
        preferred_cycle_id=preferred,
        period_end=period_end,
    )
    if not active:
        active = scenario_ref

    status_fields = derive_status_fields(active)
    temporal_fields = _derive_temporal_fields(
        analysis_cycles,
        active,
        {**raw_gf, "analysis_period_start": period_start, "analysis_period_end": period_end},
    )
    return {
        "farm_id": farm_id,
        "farm_name": farm_name,
        "cycle_id": active.get("cycle_id"),
        "period": cycle_period(active),
        "analysis_period_start": period_start,
        "analysis_period_end": period_end,
        **temporal_fields,
        **status_fields,
    }


def cycle_dropdown_options(farm_cycles: list[dict]) -> list[dict[str, str]]:
    """Opções para gf-cycle-dropdown a partir dos ciclos da fazenda."""
    opts: list[dict[str, str]] = []
    for c in farm_cycles:
        cid = c.get("cycle_id")
        if not cid:
            continue
        opts.append({"label": format_cycle_period_label(c), "value": cid})
    return sorted(opts, key=lambda o: o["label"], reverse=True)


def normalize_period(record: Any) -> str | None:
    """Extrai reporting_period de um registro (YYYY-MM, YYYY ou range)."""
    if record is None:
        return None
    if isinstance(record, str):
        s = record.strip()
        if _PERIOD_RE.match(s) or _YEAR_RE.match(s) or _DATE_RANGE_RE.match(s):
            return s
        return None
    if not isinstance(record, dict):
        return None

    for key in ("reporting_period", "period"):
        val = record.get(key)
        if isinstance(val, str) and val.strip():
            s = val.strip()
            if _PERIOD_RE.match(s) or _YEAR_RE.match(s) or _DATE_RANGE_RE.match(s):
                return s

    for nested_key in ("raw_file", "evidence_package", "payload_json", "payload"):
        nested = record.get(nested_key)
        if isinstance(nested, dict):
            p = normalize_period(nested)
            if p:
                return p
    return None


def period_matches(period_a: str | None, period_b: str | None) -> bool:
    if not period_a or not period_b:
        return False
    return period_a.strip() == period_b.strip()


def _period_year(period: str) -> str | None:
    match = _PERIOD_RE.match(period or "")
    return match.group(1) if match else None


def format_period_label(period: str) -> str:
    """Ex.: 2026-01 -> Mai/2026; 2025 -> 2025; range -> 01/06/2026 a 07/06/2026."""
    if not period:
        return "—"
    range_match = _DATE_RANGE_RE.match(period.strip())
    if range_match:
        start, end = range_match.group(1), range_match.group(2)

        def _br_date(iso_date: str) -> str:
            year, month, day = iso_date.split("-")
            return f"{day}/{month}/{year}"

        return f"{_br_date(start)} a {_br_date(end)}"
    if _YEAR_RE.match(period.strip()):
        return period.strip()
    year_range = _YEAR_RANGE_RE.match(period.strip())
    if year_range:
        return f"{year_range.group(1)} a {year_range.group(2)}"
    match = _PERIOD_RE.match(period.strip())
    if match:
        year, month = match.group(1), match.group(2)
        return f"{MONTH_LABELS.get(month, month)}/{year}"
    return period


def format_cycle_period_label(cycle: dict | None) -> str:
    """Rótulo de período para exibição na UI (ciclo ou string)."""
    if not cycle:
        return "—"
    if isinstance(cycle, str):
        return format_period_label(cycle)
    if cycle.get("period_label"):
        return str(cycle["period_label"])
    coverage = cycle.get("temporal_coverage") or {}
    if coverage.get("label"):
        return str(coverage["label"])
    return format_period_label(cycle.get("reporting_period") or "")


def format_status_badge_label(normalized: dict[str, Any]) -> str:
    from services.cycle_status_service import managerial_status_label

    label = managerial_status_label(normalized.get("approval_status"))
    if label != "—":
        return label
    return normalized.get("cycle_status") or "—"


def intensity_trend_from_cycles(cycles: list[dict]) -> tuple[list[str], list[float]]:
    """Intensidade por período (série base já agregada por sum(co2e)/sum(leite))."""
    from utils.temporal_series import expand_cycles_period_series

    series = expand_cycles_period_series(cycles)
    labels: list[str] = []
    values: list[float] = []
    for r in series:
        if r.get("intensity") is None:
            continue
        labels.append(r.get("period_label") or str(r.get("period_key") or ""))
        values.append(float(r["intensity"]))
    return labels, values


def is_all_periods(filters: dict[str, Any]) -> bool:
    """Deprecated: modo multi-período removido do fluxo principal."""
    return False


def get_period_mode(filters: dict[str, Any] | None) -> str:
    """Deprecated: retorna 'single' para compatibilidade."""
    return "single"


def period_in_context(period: str | None, filters: dict[str, Any], active_cycle: dict | None = None) -> bool:
    """Verifica se um período pertence ao contexto do filtro (ciclo ativo)."""
    if not period:
        return False

    gf = normalize_global_filter(filters)
    if is_no_farm_selected(gf):
        return False

    store_period = gf.get("period")
    if store_period and period_matches(period, store_period):
        return True

    cycle_id = gf.get("cycle_id")
    if cycle_id and active_cycle and active_cycle.get("cycle_id") == cycle_id:
        active_p = cycle_period(active_cycle)
        if active_p and period_matches(period, active_p):
            return True

    if store_period:
        return period_matches(period, store_period)

    return not cycle_id


def filter_cycles_by_context(
    cycles: list[dict],
    filters: dict[str, Any],
    active_cycle: dict | None = None,
) -> list[dict]:
    """Filtra ciclos por fazenda e ciclo ativo (sem filtro por status multi-select)."""
    gf = normalize_global_filter(filters)
    if is_no_farm_selected(gf):
        return []

    by_property = filter_by_farm(cycles, gf.get("farm_id"))
    cycle_id = gf.get("cycle_id")
    if not cycle_id:
        return by_property

    matched = [c for c in by_property if c.get("cycle_id") == cycle_id]
    if matched:
        return matched
    if active_cycle and active_cycle.get("cycle_id") == cycle_id:
        if cycle_belongs_to_farm(active_cycle, gf.get("farm_id")):
            return [active_cycle]
    return []


def build_context_index(cycles: list[dict]) -> dict[str, dict[str, str]]:
    """Mapa ref (pipeline_run_id/cycle_id) -> {property_id, period}."""
    index: dict[str, dict[str, str]] = {}
    for c in cycles:
        pid = normalize_property_id(c)
        period = cycle_period(c) or normalize_period(c) or ""
        if not pid:
            continue
        entry = {"property_id": pid, "period": period or ""}
        run_id = c.get("pipeline_run_id")
        if run_id:
            index[str(run_id)] = entry
        cycle_id = c.get("cycle_id")
        if cycle_id:
            index[str(cycle_id)] = entry
    return index


def _resolve_event_context(event: dict, index: dict[str, dict[str, str]]) -> tuple[str | None, str | None]:
    """Resolve property_id e período de um evento via índice de ciclos."""
    pid = normalize_property_id(event)
    period = normalize_period(event)
    if pid and period:
        return pid, period

    for key in ("pipeline_execution_id", "pipeline_run_id", "aggregate_id"):
        ref = event.get(key)
        if ref and str(ref) in index:
            entry = index[str(ref)]
            return pid or entry.get("property_id"), period or entry.get("period") or None

    payload = event.get("payload_json") or event.get("payload") or {}
    cyc = payload.get("cycle_id")
    if cyc and str(cyc) in index:
        entry = index[str(cyc)]
        return pid or entry.get("property_id"), period or entry.get("period") or None

    return pid, period


def filter_events_by_context(
    events: list[dict],
    cycles: list[dict],
    filters: dict[str, Any],
    active_cycle: dict | None = None,
) -> list[dict]:
    """Filtra eventos de proveniência por propriedade e ciclo ativo."""
    gf = normalize_global_filter(filters)
    context_cycles = filter_cycles_by_context(cycles, gf, active_cycle)
    allowed_pids = {normalize_property_id(c) for c in context_cycles if normalize_property_id(c)}
    index = build_context_index(cycles)
    farm_id = gf.get("farm_id")

    out = []
    for e in events:
        pid, period = _resolve_event_context(e, index)

        if farm_id and pid and pid != farm_id:
            continue
        if farm_id and not pid:
            continue
        if farm_id and pid not in allowed_pids:
            continue

        if not period_in_context(period, gf, active_cycle):
            continue
        out.append(e)
    return out


def filter_evidence_from_cycles(cycles: list[dict], filters: dict[str, Any], active_cycle: dict | None = None) -> list[dict]:
    """Retorna pacotes de evidência dos ciclos no contexto."""
    filtered = filter_cycles_by_context(cycles, filters, active_cycle)
    return [c.get("evidence_package") for c in filtered if (c.get("evidence_package") or {}).get("evidence_package_id")]


def apply_global_filters(
    data: list[dict],
    filters: dict[str, Any],
    data_type: str = "cycles",
    *,
    all_cycles: list[dict] | None = None,
    active_cycle: dict | None = None,
) -> list[dict]:
    """Dispatcher de filtragem por tipo de dado."""
    if data_type == "cycles":
        return filter_cycles_by_context(data, filters, active_cycle)
    if data_type == "events":
        return filter_events_by_context(data, all_cycles or [], filters, active_cycle)
    if data_type == "evidence":
        return filter_evidence_from_cycles(all_cycles or data, filters, active_cycle)
    return filter_cycles_by_context(data, filters, active_cycle)


def resolve_active_cycle_for_context(
    cycle: dict | None,
    filtered_cycles: list[dict],
    filters: dict[str, Any] | None = None,
) -> dict | None:
    """Ciclo ativo coerente com o contexto de filtro."""
    farm_id = (filters or {}).get("farm_id")
    return resolve_active_cycle(cycle, filtered_cycles, farm_id=farm_id)


def resolve_context_cycle(
    cycle: dict | None,
    filtered_cycles: list[dict],
    context_cycle_id: str | None = None,
    *,
    farm_id: str | None = None,
) -> dict | None:
    """Resolve ciclo ativo apenas dentro do conjunto filtrado (sem cross-farm)."""
    preferred = context_cycle_id
    if preferred:
        for c in filtered_cycles:
            if c.get("cycle_id") == preferred:
                return c
    if cycle and cycle.get("cycle_id"):
        cid = cycle.get("cycle_id")
        for c in filtered_cycles:
            if c.get("cycle_id") == cid:
                return c
        if farm_id and cycle_belongs_to_farm(cycle, farm_id):
            return cycle
    return resolve_active_cycle(cycle, filtered_cycles, farm_id=farm_id)


def is_empty_context(filtered_cycles: list[dict], filters: dict[str, Any] | None = None) -> bool:
    if is_no_farm_selected(filters):
        return True
    return len(filtered_cycles) == 0


def format_filter_badge(filters: dict[str, Any], options: dict[str, Any] | None = None) -> str:
    """Rótulo compacto do filtro ativo para o navbar."""
    gf = normalize_global_filter(filters)
    options = options or {}

    if is_no_farm_selected(gf):
        return "Selecione uma fazenda para visualizar os dados."

    prop_label = gf.get("farm_name") or get_selected_farm_label(
        gf.get("farm_id"), options.get("properties") or []
    )
    period_label = gf.get("period_display_label") or format_cycle_period_label(
        {"reporting_period": gf.get("period"), "period_label": None}
    )
    granularity = GRANULARITY_LABELS.get(gf.get("granularity") or "", gf.get("granularity") or "—")

    return f"Filtrando por: {prop_label} • {period_label} • {granularity}"


def format_page_title_with_filter(
    base_title: str,
    filters: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> str:
    gf = normalize_global_filter(filters)
    if is_no_farm_selected(gf):
        return base_title
    badge = format_filter_badge(gf, options)
    if badge.startswith("Filtrando por: "):
        return f"{base_title} — {badge.replace('Filtrando por: ', '')}"
    return base_title


def default_upload_period(filters: dict[str, Any]) -> str:
    gf = normalize_global_filter(filters)
    if gf.get("period"):
        return gf["period"]
    return "2026-01"


def default_upload_property(filters: dict[str, Any], cycle: dict | None = None) -> str:
    gf = normalize_global_filter(filters)
    farm_id = gf.get("farm_id")
    if farm_id:
        return farm_id
    return (cycle or {}).get("property_id", "FARM-001")
