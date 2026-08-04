"""Mapeamento e seleção de fatores de emissão (IPCC + ECOFARM observado)."""

from __future__ import annotations

from typing import Any

import config
from services.calculation_view_service import (
    _FACTOR_GROUP_LABELS,
    _aggregate_tier2_observed,
    _normalized_records,
    _select_enteric_observed_rows,
    _tier1_enteric_values,
)
from utils.date_helpers import now_iso

DEFAULT_FACTOR_METHODOLOGY = "IPCC/IDF-compatible"

# formula_id → grupos de fatores editáveis na revisão
FORMULA_FACTOR_GROUPS: dict[str, list[str]] = {
    "enteric_fermentation_ch4": ["enteric_ch4_kg_per_animal"],
    "manure_management_ch4": ["manure_kg_per_kg_bw_per_day", "manure_ch4_kg_per_kg_manure"],
    "fertilizer_n2o": ["fertilizer_factors"],
    "energy_co2": ["energy_co2_kg_per_unit"],
    "total_ghg_co2e": ["gwp"],
}

FORMULA_SUB_IDS: dict[str, str] = {
    "enteric_fermentation_ch4": "enteric",
    "manure_management_ch4": "manure",
    "fertilizer_n2o": "fertilizer",
    "energy_co2": "energy",
    "total_ghg_co2e": "total",
}

_PROFILE_IPCC_DEFAULT = "ipcc_default"
_PROFILE_IPCC_CURRENT = "ipcc_current"
_PROFILE_ECOFARM_TCO2E = "ecofarm:tco2e_implied"
_PROFILE_ECOFARM_EF = "ecofarm:ef_enteric"


def get_factor_groups_for_formula(formula_id: str) -> list[str]:
    return list(FORMULA_FACTOR_GROUPS.get(formula_id, []))


def resolve_sub_id_for_formula(formula_id: str) -> str | None:
    return FORMULA_SUB_IDS.get(formula_id)


def resolve_sub_id(item: dict) -> str | None:
    return (
        item.get("sub_id")
        or item.get("subcalculation_id")
        or resolve_sub_id_for_formula(item.get("formula_id") or "")
    )


def _subcalculation(cycle: dict, sub_id: str | None) -> dict | None:
    if not sub_id:
        return None
    for sub in (cycle.get("calculation") or {}).get("subcalculations") or []:
        if sub.get("id") == sub_id:
            return sub
    return None


def _synthesize_factors_from_subcalculations(cycle: dict) -> dict[str, Any]:
    """Monta factors_used a partir dos subcálculos (ciclos legados sem bloco global)."""
    merged: dict[str, Any] = {}
    for sub in (cycle.get("calculation") or {}).get("subcalculations") or []:
        for group, data in (sub.get("factors") or {}).items():
            if not isinstance(data, dict):
                continue
            bucket = merged.setdefault(group, {})
            bucket.update(data)
    return merged


def get_effective_factors_used(cycle: dict) -> dict[str, Any]:
    """Fatores efetivos: factors_used global ou síntese dos subcálculos."""
    calc = cycle.get("calculation") or {}
    factors = calc.get("factors_used")
    if isinstance(factors, dict) and factors:
        return factors
    return _synthesize_factors_from_subcalculations(cycle)


def _factors_used(cycle: dict) -> dict[str, Any]:
    return get_effective_factors_used(cycle)


def _filter_factor_data_for_sub(group: str, data: dict, sub: dict | None) -> dict:
    """Restringe fatores às chaves usadas no subcálculo (categorias/vetores do inventário)."""
    if not sub or not isinstance(data, dict):
        return data
    inputs = sub.get("inputs") or {}
    if group == "energy_co2_kg_per_unit":
        vectors = inputs.get("energy_consumption_by_vector") or {}
        if vectors:
            return {k: v for k, v in data.items() if k in vectors}
    if group in (
        "enteric_ch4_kg_per_animal",
        "manure_kg_per_kg_bw_per_day",
        "manure_ch4_kg_per_kg_manure",
    ):
        headcounts = inputs.get("headcounts_by_category") or {}
        if headcounts:
            return {k: v for k, v in data.items() if k in headcounts}
    return data


def _headcounts(cycle: dict) -> dict[str, float]:
    calc = cycle.get("calculation") or {}
    inputs = calc.get("inputs") or {}
    hc = inputs.get("headcounts_by_category") or {}
    return {k: float(v) for k, v in hc.items() if v}


def _energy_vectors(cycle: dict) -> list[str]:
    calc = cycle.get("calculation") or {}
    inputs = calc.get("inputs") or {}
    return list((inputs.get("energy_consumption_by_vector") or {}).keys())


def _load_ipcc_defaults(group: str, cycle: dict) -> dict[str, Any]:
    from services import direct_imports as di

    if group == "enteric_ch4_kg_per_animal":
        from emissions.defaults import default_enteric_ch4_kg_per_animal_yearly
        from emissions.factor_alignment import align_enteric_factors_to_scope

        raw = default_enteric_ch4_kg_per_animal_yearly()
        scope = (cycle.get("calculation") or {}).get("temporal", {}).get("scope", "MONTHLY")
        temporal = di.TemporalScope.MONTHLY if str(scope).upper() == "MONTHLY" else di.TemporalScope.YEARLY
        return align_enteric_factors_to_scope(raw, temporal_scope=temporal, auto_prorate=True)

    if group == "manure_kg_per_kg_bw_per_day":
        from emissions.defaults import default_manure_kg_per_kg_bw_per_day
        return dict(default_manure_kg_per_kg_bw_per_day())

    if group == "manure_ch4_kg_per_kg_manure":
        from emissions.defaults import default_manure_ch4_kg_per_kg_manure
        return dict(default_manure_ch4_kg_per_kg_manure())

    if group == "energy_co2_kg_per_unit":
        from emissions.defaults import default_energy_co2_kg_per_unit_yearly_basis
        from emissions.factor_alignment import align_energy_factors_to_scope

        raw = default_energy_co2_kg_per_unit_yearly_basis()
        vectors = _energy_vectors(cycle)
        filtered = {k: v for k, v in raw.items() if not vectors or k in vectors}
        scope = (cycle.get("calculation") or {}).get("temporal", {}).get("scope", "MONTHLY")
        temporal = di.TemporalScope.MONTHLY if str(scope).upper() == "MONTHLY" else di.TemporalScope.YEARLY
        return align_energy_factors_to_scope(filtered, temporal_scope=temporal, auto_prorate=True)

    if group == "fertilizer_factors":
        from emissions.defaults import default_fertilizer_factors
        return dict(default_fertilizer_factors())

    if group == "gwp":
        if di.gwp_ipcc_ar4:
            return dict(di.gwp_ipcc_ar4())
        return dict(config.DEFAULT_GWP)

    return {}


def _ecofarm_enteric_uniform_ef(cycle: dict) -> tuple[dict[str, float] | None, str | None]:
    """Deriva fatores entericos uniformes a partir do ECOFARM observado."""
    records = _normalized_records(cycle)
    observed_rows = _select_enteric_observed_rows(cycle, records)
    if not observed_rows:
        return None, None

    headcounts = _headcounts(cycle)
    if not headcounts:
        return None, None

    total_head = sum(headcounts.values())
    if total_head <= 0:
        return None, None

    tier2 = _aggregate_tier2_observed(observed_rows)
    gwp_ch4 = float(_tier1_enteric_values(cycle).get("gwp_ch4") or config.DEFAULT_GWP.get("CH4", 25))

    if tier2.get("enteric_tco2e_t") is not None:
        ch4_total = float(tier2["enteric_tco2e_t"]) * 1000.0 / gwp_ch4
        ef_uniform = ch4_total / total_head
        factors = {cat: ef_uniform for cat, n in headcounts.items() if n > 0}
        return factors, _PROFILE_ECOFARM_TCO2E

    ef_raw = tier2.get("ef_enteric_kg_ch4")
    if ef_raw is None:
        return None, None

    ef_val = float(ef_raw)
    # Heurística: valores muito altos costumam ser emissão total do período, não por cabeça.
    if ef_val > 500:
        ef_val = ef_val / total_head

    factors = {cat: ef_val for cat, n in headcounts.items() if n > 0}
    return factors, _PROFILE_ECOFARM_EF


def list_factor_profiles(cycle: dict, formula_id: str) -> list[dict[str, Any]]:
    """Perfis de fatores disponíveis para um item de revisão."""
    groups = get_factor_groups_for_formula(formula_id)
    if not groups:
        return []

    factors_used = _factors_used(cycle)
    ecofarm_enteric, ecofarm_profile_id = _ecofarm_enteric_uniform_ef(cycle)
    profiles: list[dict[str, Any]] = []

    for group in groups:
        current = dict(factors_used.get(group) or {})
        default_vals = _load_ipcc_defaults(group, cycle)

        options: list[dict[str, Any]] = [
            {
                "profile_id": f"{group}:{_PROFILE_IPCC_CURRENT}",
                "group": group,
                "label": "Fatores em uso no cálculo",
                "source": "pipeline",
                "values": current,
                "description": "Mantém os fatores já aplicados neste ciclo.",
            },
            {
                "profile_id": f"{group}:{_PROFILE_IPCC_DEFAULT}",
                "group": group,
                "label": "IPCC Tier 1 (padrão)",
                "source": "ipcc",
                "values": default_vals,
                "description": "Defaults IPCC com alinhamento ao escopo temporal.",
            },
        ]

        if group == "enteric_ch4_kg_per_animal" and ecofarm_enteric:
            if ecofarm_profile_id == _PROFILE_ECOFARM_TCO2E:
                label = "ECOFARM — fator implícito (enteric_tco2e ÷ rebanho)"
                desc = "Deriva kg CH₄/cab/período a partir da emissão observada no arquivo."
            else:
                label = "ECOFARM — ef_enteric_kg_ch4 observado"
                desc = "Usa ef_enteric_kg_ch4 do dado normalizado (ajustado por rebanho se agregado)."

            options.append({
                "profile_id": f"{group}:{ecofarm_profile_id}",
                "group": group,
                "label": label,
                "source": "ecofarm",
                "values": ecofarm_enteric,
                "description": desc,
            })

        active = (cycle.get("calculation_params") or {}).get("factor_selections") or {}
        active_id = active.get(group, {}).get("profile_id")

        profiles.append({
            "group": group,
            "title": _FACTOR_GROUP_LABELS.get(group, group),
            "options": options,
            "active_profile_id": active_id,
            "current_values": current,
        })

    return profiles


def _format_factor_preview(values: dict[str, Any], max_keys: int = 3) -> str:
    if not values:
        return "—"
    items = list(values.items())[:max_keys]
    parts = [f"{k}: {round(float(v), 4) if isinstance(v, (int, float)) else v}" for k, v in items]
    suffix = f" (+{len(values) - max_keys})" if len(values) > max_keys else ""
    return "; ".join(parts) + suffix


def list_factor_options_for_ui(cycle: dict, item: dict) -> list[dict[str, Any]]:
    """Opções formatadas para dropdown na UI."""
    formula_id = item.get("formula_id") or ""
    blocks = list_factor_profiles(cycle, formula_id)
    ui_blocks: list[dict[str, Any]] = []

    for block in blocks:
        group = block["group"]
        select_options = []
        for opt in block["options"]:
            preview = _format_factor_preview(opt.get("values") or {})
            select_options.append({
                "label": f"{opt['label']} — {preview}",
                "value": opt["profile_id"],
            })

        default_value = block.get("active_profile_id")
        if not default_value and select_options:
            default_value = select_options[0]["value"]

        ui_blocks.append({
            "group": group,
            "title": block["title"],
            "options": select_options,
            "default_value": default_value,
        })

    return ui_blocks


def resolve_profile_values(cycle: dict, profile_id: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Resolve profile_id → (group, values, metadata)."""
    if ":" not in profile_id:
        raise ValueError(f"profile_id inválido: {profile_id}")

    group, profile_key = profile_id.rsplit(":", 1)
    blocks = []
    for fid, groups in FORMULA_FACTOR_GROUPS.items():
        if group in groups:
            blocks = list_factor_profiles(cycle, fid)
            break

    for block in blocks:
        if block["group"] != group:
            continue
        for opt in block["options"]:
            if opt["profile_id"] == profile_id:
                return group, dict(opt.get("values") or {}), {
                    "profile_id": profile_id,
                    "source": opt.get("source"),
                    "label": opt.get("label"),
                }

    if profile_key == _PROFILE_IPCC_DEFAULT:
        return group, _load_ipcc_defaults(group, cycle), {
            "profile_id": profile_id,
            "source": "ipcc",
            "label": "IPCC Tier 1 (padrão)",
        }

    if profile_key == _PROFILE_IPCC_CURRENT:
        current = dict(_factors_used(cycle).get(group) or {})
        return group, current, {
            "profile_id": profile_id,
            "source": "pipeline",
            "label": "Fatores em uso no cálculo",
        }

    raise ValueError(f"Perfil de fator não encontrado: {profile_id}")


def build_factor_params(cycle: dict, group: str, values: dict[str, Any], *, profile_meta: dict) -> dict[str, Any]:
    """Atualiza calculation_params com seleção de fatores."""
    params = dict(cycle.get("calculation_params") or {})
    selections = dict(params.get("factor_selections") or {})
    selections[group] = {
        **profile_meta,
        "group": group,
        "applied_at": now_iso(),
    }
    params["factor_selections"] = selections

    if profile_meta.get("profile_id", "").endswith(f":{_PROFILE_IPCC_DEFAULT}"):
        params.pop(group, None)
    else:
        params[group] = {k: float(v) for k, v in values.items()}

    return params


def build_factor_rows_for_display(cycle: dict, item: dict) -> list[dict[str, Any]]:
    """Linhas atuais dos fatores do item para tabela na UI."""
    formula_id = item.get("formula_id") or ""
    sub_id = resolve_sub_id(item)
    sub = _subcalculation(cycle, sub_id)
    sub_factors: dict[str, Any] = (sub or {}).get("factors") or {}

    rows: list[dict[str, Any]] = []
    fert_labels = {
        "direct_n2o_emission_factor": "EF direto N₂O",
        "indirect_n2o_emission_factor": "EF indireto N₂O",
        "fraction_n_volatilized": "Fração N volatilizada",
    }
    for group in get_factor_groups_for_formula(formula_id):
        data = sub_factors.get(group)
        if data is None:
            data = _factors_used(cycle).get(group) or {}
        data = _filter_factor_data_for_sub(group, dict(data) if isinstance(data, dict) else {}, sub)
        for k, v in data.items():
            rows.append({
                "group": group,
                "factor_key": k,
                "grupo": _FACTOR_GROUP_LABELS.get(group, group),
                "chave": fert_labels.get(k, k) if group == "fertilizer_factors" else k,
                "valor": v,
            })
    return rows


def build_factor_params_from_edits(cycle: dict, edits: list[dict[str, Any]]) -> dict[str, Any]:
    """Reconstrói calculation_params a partir de valores editados na UI."""
    from services.calculation_view_service import rebuild_calculation_params_from_factor_inputs

    factor_ids = [{"group": e["group"], "key": e["factor_key"]} for e in edits]
    factor_values = [e["value"] for e in edits]
    params = rebuild_calculation_params_from_factor_inputs(factor_ids, factor_values, cycle)

    selections = dict(params.get("factor_selections") or {})
    for edit in edits:
        group = edit["group"]
        selections[group] = {
            "profile_id": f"{group}:manual_edit",
            "group": group,
            "source": "manual",
            "label": "Edição manual",
            "applied_at": now_iso(),
        }
    params["factor_selections"] = selections
    return params


def get_default_factor_methodology(cycle: dict | None = None) -> str:
    """Metodologia padrão dos fatores (IPCC)."""
    if cycle:
        calc = cycle.get("calculation") or {}
        method = calc.get("method") or {}
        return (
            calc.get("methodology")
            or method.get("methodology_label")
            or DEFAULT_FACTOR_METHODOLOGY
        )
    return DEFAULT_FACTOR_METHODOLOGY


def build_factor_baseline(factor_rows: list[dict]) -> list[dict[str, Any]]:
    """Snapshot dos valores atuais para detectar alteração na UI."""
    baseline: list[dict[str, Any]] = []
    for row in factor_rows:
        try:
            val = float(row.get("valor") or 0)
        except (TypeError, ValueError):
            val = 0.0
        baseline.append({
            "group": row["group"],
            "factor_key": row["factor_key"],
            "value": val,
        })
    return baseline


def split_changed_factor_edits(
    baseline: list[dict],
    edits: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Separa edições que realmente mudaram em relação ao baseline."""
    baseline_map = {
        (b["group"], b["factor_key"]): float(b["value"])
        for b in baseline
    }
    changed: list[dict] = []
    unchanged: list[dict] = []
    for edit in edits:
        key = (edit["group"], edit["factor_key"])
        new_val = float(edit["value"])
        if key not in baseline_map or baseline_map[key] != new_val:
            changed.append(edit)
        else:
            unchanged.append(edit)
    return changed, unchanged


def resolve_item_factor_methodology(item: dict, cycle: dict) -> dict[str, Any]:
    """Metodologia do item: default IPCC + applied quando houve edição manual."""
    stored = item.get("factor_methodology") or {}
    default = stored.get("default") or get_default_factor_methodology(cycle)
    return {
        "default": default,
        "applied": stored.get("applied"),
        "updated_at": stored.get("updated_at"),
        "updated_by": stored.get("updated_by"),
    }
