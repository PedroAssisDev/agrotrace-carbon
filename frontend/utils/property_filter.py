"""Filtro global por propriedade — lógica centralizada.

Todas as telas usam estas funções para respeitar a seleção de propriedades do
filtro global. Convenção: ``selected_ids`` vazio ou ``None`` significa "todas
as propriedades".
"""

from __future__ import annotations

from typing import Any

# Aliases conhecidos de IDs legados (espelha property_registry, evitando ciclo de import).
_LEGACY_ALIASES = {"P-1": "FARM-001"}


def _canonical(pid: str | None) -> str | None:
    if pid is None:
        return None
    return _LEGACY_ALIASES.get(pid, pid)


def get_all_property_ids(record: Any) -> set[str]:
    """Coleta todos os IDs de propriedade presentes em um registro (incl. aninhados)."""
    if record is None:
        return set()
    if isinstance(record, str):
        pid = _canonical(record)
        return {pid} if pid else set()
    if not isinstance(record, dict):
        return set()

    ids: set[str] = set()
    for key in ("property_id", "farm_id", "property", "farm"):
        val = record.get(key)
        if isinstance(val, str) and val:
            ids.add(_canonical(val))

    for nested_key in ("raw_file", "evidence_package", "payload_json", "payload"):
        nested = record.get(nested_key)
        if isinstance(nested, dict):
            ids.update(get_all_property_ids(nested))

    return ids


def normalize_property_id(record: Any) -> str | None:
    """Extrai o property_id canônico de um registro heterogêneo.

    Procura, em ordem: property_id, farm_id, property, farm, e campos
    aninhados em raw_file / evidence_package.
    """
    if record is None:
        return None
    if isinstance(record, str):
        return _canonical(record)
    if not isinstance(record, dict):
        return None

    for key in ("property_id", "farm_id", "property", "farm", "property_name", "farm_name"):
        val = record.get(key)
        if isinstance(val, str) and val:
            return _canonical(val)

    for nested_key in ("raw_file", "evidence_package", "payload_json", "payload"):
        nested = record.get(nested_key)
        if isinstance(nested, dict):
            nested_id = normalize_property_id(nested)
            if nested_id:
                return nested_id

    return None


def is_all_selected(selected_ids: list[str] | None) -> bool:
    """Filtro vazio/None => todas as propriedades."""
    return not selected_ids


def _selected_set(selected_ids: list[str] | None) -> set[str]:
    return {_canonical(s) for s in (selected_ids or []) if s}


def filter_by_selected_properties(records: list[dict], selected_ids: list[str] | None) -> list[dict]:
    """Filtra registros cujo property_id normalizado esteja na seleção."""
    if is_all_selected(selected_ids):
        return list(records)
    wanted = _selected_set(selected_ids)
    return [r for r in records if wanted & get_all_property_ids(r)]


def filter_by_farm(records: list[dict], farm_id: str | None) -> list[dict]:
    """Filtra registros pela fazenda selecionada. Sem farm_id => lista vazia."""
    if not farm_id:
        return []
    wanted = {_canonical(farm_id)}
    return [r for r in records if wanted & get_all_property_ids(r)]


def get_selected_farm_label(
    farm_id: str | None,
    properties: list[dict] | None = None,
) -> str:
    """Rótulo amigável da fazenda selecionada."""
    if not farm_id:
        return "Nenhuma fazenda selecionada"
    name = _property_name(farm_id, properties)
    return name or farm_id


def format_page_title_for_farm(
    base_title: str,
    farm_id: str | None,
    properties: list[dict] | None = None,
) -> str:
    """Ex.: 'Dashboard — Fazenda Santa Clara'."""
    if not farm_id:
        return base_title
    return f"{base_title} — {get_selected_farm_label(farm_id, properties)}"


def get_selected_property_label(
    selected_ids: list[str] | None,
    properties: list[dict] | None = None,
) -> str:
    """Rótulo amigável da seleção atual (legado multi-select; scripts de validação)."""
    if is_all_selected(selected_ids):
        return "Todas as propriedades"
    wanted = [s for s in (selected_ids or []) if s]
    if len(wanted) == 1:
        return get_selected_farm_label(wanted[0], properties)
    return f"{len(wanted)} propriedades selecionadas"


def format_page_title(
    base_title: str,
    selected_ids: list[str] | None,
    properties: list[dict] | None = None,
) -> str:
    """Ex.: 'Dashboard — Fazenda Santa Clara' (legado multi-select)."""
    if is_all_selected(selected_ids):
        return base_title
    if len(selected_ids or []) == 1:
        return format_page_title_for_farm(base_title, selected_ids[0], properties)
    return f"{base_title} — {get_selected_property_label(selected_ids, properties)}"


def _property_name(property_id: str, properties: list[dict] | None) -> str | None:
    canonical = _canonical(property_id)
    for p in properties or []:
        if p.get("property_id") == canonical:
            return p.get("name") or canonical
    return canonical


def build_pipeline_run_index(cycles: list[dict]) -> dict[str, str]:
    """Mapa pipeline_run_id -> property_id (canônico) a partir dos ciclos."""
    index: dict[str, str] = {}
    for c in cycles:
        pid = normalize_property_id(c)
        if not pid:
            continue
        run_id = c.get("pipeline_run_id")
        if run_id:
            index[str(run_id)] = pid
        cycle_id = c.get("cycle_id")
        if cycle_id:
            index[str(cycle_id)] = pid
    return index


def filter_provenance_events(
    events: list[dict],
    cycles: list[dict],
    selected_ids: list[str] | None,
) -> list[dict]:
    """Filtra eventos de proveniência pela propriedade via índice de pipeline/ciclo."""
    if is_all_selected(selected_ids):
        return list(events)

    index = build_pipeline_run_index(cycles)
    wanted = _selected_set(selected_ids)
    out = []
    for e in events:
        # Tenta property_id direto no evento (raro) ou via pipeline/aggregate/cycle.
        pid = normalize_property_id(e)
        if pid is None:
            for key in ("pipeline_execution_id", "pipeline_run_id", "aggregate_id"):
                ref = e.get(key)
                if ref and str(ref) in index:
                    pid = index[str(ref)]
                    break
            else:
                payload = e.get("payload_json") or e.get("payload") or {}
                cyc = payload.get("cycle_id")
                if cyc and str(cyc) in index:
                    pid = index[str(cyc)]
        if pid in wanted:
            out.append(e)
    return out


def resolve_active_cycle(
    cycle: dict | None,
    filtered_cycles: list[dict],
    *,
    farm_id: str | None = None,
) -> dict | None:
    """Se o ciclo ativo não pertence ao filtro, usa o mais recente do conjunto filtrado."""
    if cycle and cycle.get("cycle_id"):
        pid = normalize_property_id(cycle)
        in_set = any(c.get("cycle_id") == cycle.get("cycle_id") for c in filtered_cycles)
        if in_set:
            return cycle
        if farm_id and pid:
            if pid != farm_id and farm_id not in get_all_property_ids(cycle):
                pass
            else:
                return cycle
        elif not farm_id:
            return cycle
    if filtered_cycles:
        return max(filtered_cycles, key=lambda c: c.get("updated_at") or c.get("created_at") or "")
    return None


def aggregate_by_property(records: list[dict]) -> dict[str, list[dict]]:
    """Agrupa registros por property_id normalizado."""
    grouped: dict[str, list[dict]] = {}
    for record in records:
        pid = normalize_property_id(record)
        if not pid:
            for nested_pid in get_all_property_ids(record):
                grouped.setdefault(nested_pid, []).append(record)
            continue
        grouped.setdefault(pid, []).append(record)
    return grouped


def aggregate_calculation_metrics(cycles: list[dict]) -> dict[str, Any]:
    """Agrega métricas de cálculo para o dashboard multi-propriedade."""
    total_co2e = 0.0
    by_source: dict[str, float] = {}
    intensities: list[float] = []

    for c in cycles:
        calc = c.get("calculation") or {}
        total_co2e += float(calc.get("co2e_total_kg") or 0)
        intensity = calc.get("co2e_intensity_per_milk_liter")
        if intensity:
            intensities.append(float(intensity))
        for src, val in (calc.get("by_source") or {}).items():
            by_source[src] = by_source.get(src, 0.0) + float(val or 0)

    avg_intensity = sum(intensities) / len(intensities) if intensities else 0.0
    return {
        "co2e_total_kg": total_co2e,
        "by_source": by_source,
        "avg_intensity": avg_intensity,
        "cycle_count": len(cycles),
    }
