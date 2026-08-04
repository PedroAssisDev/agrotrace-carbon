"""Contexto de pipeline — resolução de propriedade e avisos demo."""

from __future__ import annotations

from utils.global_filter import get_farm_id


def get_selected_farm(global_filter) -> str | None:
    return get_farm_id(global_filter)


def append_demo_warning(cycle: dict, used_mock: bool) -> dict:
    if not used_mock:
        return cycle
    from services.mock_data import MOCK_FARM

    cycle.setdefault("warnings", []).append({
        "step": "pipeline",
        "message": f"Modo demonstração: usando {MOCK_FARM['name']} ({MOCK_FARM['property_id']}) — "
                   "selecione uma fazenda no filtro para ciclo real.",
    })
    return cycle


def resolve_pipeline_property(farm_id, catalog, fallback_id, fallback_name):
    """Determina (property_id, property_name) para a pipeline a partir do filtro global."""
    catalog = catalog or []

    def _name(pid: str) -> str:
        for p in catalog:
            if p.get("property_id") == pid:
                return p.get("name") or pid
        return fallback_name

    if farm_id:
        return farm_id, _name(farm_id)
    return None, None
