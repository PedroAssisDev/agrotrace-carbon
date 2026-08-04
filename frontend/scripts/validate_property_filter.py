"""Validação headless do filtro global de propriedades.

Usa IDs canônicos e valida label separadamente (não depende de "Embrapa P-1").
Roda sobre catálogo isolado / fixtures inline.

Uso:
    python scripts/validate_property_filter.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from scripts._validation_env import CheckCollector, isolated_data_root, print_structured_summary  # noqa: E402
from utils.property_filter import (  # noqa: E402
    aggregate_by_property,
    aggregate_calculation_metrics,
    build_pipeline_run_index,
    filter_by_selected_properties,
    filter_provenance_events,
    format_page_title,
    get_all_property_ids,
    get_selected_property_label,
    is_all_selected,
    normalize_property_id,
)

# Catálogo canônico isolado — sem depender do ambiente operacional / Embrapa.
CANONICAL_CATALOG = [
    {"property_id": "FARM-001", "name": "Fazenda Santa Clara", "municipality": "Patos de Minas", "state": "MG"},
    {"property_id": "FARM-002", "name": "Fazenda Boa Vista", "municipality": "Uberaba", "state": "MG"},
    {"property_id": "FARM-MONTHLY-001", "name": "Fazenda Boa Vista Leiteira", "municipality": "Uberaba", "state": "MG"},
    {"property_id": "FARM-ANNUAL-001", "name": "Fazenda Santa Clara Sustentável", "municipality": "Patos de Minas", "state": "MG"},
    {"property_id": "FARM-DAILY-001", "name": "Fazenda Experimental Sensorial", "municipality": "Lavras", "state": "MG"},
]


def main() -> int:
    v = CheckCollector()
    print("== Property filter validation (IDs canônicos, fixture isolado) ==\n")

    with isolated_data_root(bootstrap=False):
        catalog = list(CANONICAL_CATALOG)

        v.check("catalogo e lista", isinstance(catalog, list) and len(catalog) >= 2)
        v.check(
            "catalogo sem duplicar ids",
            len({p["property_id"] for p in catalog}) == len(catalog),
        )

        # Asserções de ID canônico (independentes de label)
        canonical_ids = {p["property_id"] for p in catalog}
        for pid in ("FARM-001", "FARM-002", "FARM-MONTHLY-001", "FARM-ANNUAL-001", "FARM-DAILY-001"):
            v.check(f"ID canônico presente: {pid}", pid in canonical_ids)

        cycles = [
            {
                "cycle_id": "C1",
                "property_id": "FARM-001",
                "pipeline_run_id": "R1",
                "calculation": {
                    "co2e_total_kg": 100.0,
                    "by_source": {"enteric": 60.0},
                    "co2e_intensity_per_milk_liter": 0.8,
                },
            },
            {
                "cycle_id": "C2",
                "property_id": "FARM-002",
                "pipeline_run_id": "R2",
                "calculation": {
                    "co2e_total_kg": 200.0,
                    "by_source": {"enteric": 40.0},
                    "co2e_intensity_per_milk_liter": 0.6,
                },
            },
            {
                "cycle_id": "C3",
                "farm_id": "P-1",
                "pipeline_run_id": "R3",
                "calculation": {"co2e_total_kg": 50.0, "by_source": {}},
            },
        ]

        # Alias legado: ID separado do label
        v.check("normalize alias P-1 -> FARM-001 (ID)", normalize_property_id({"farm_id": "P-1"}) == "FARM-001")
        v.check(
            "normalize nested raw_file",
            normalize_property_id({"raw_file": {"property_id": "FARM-002"}}) == "FARM-002",
        )
        v.check("is_all_selected([]) verdadeiro", is_all_selected([]) and is_all_selected(None))

        v.check("filtro vazio retorna todos", len(filter_by_selected_properties(cycles, [])) == 3)
        farm1 = filter_by_selected_properties(cycles, ["FARM-001"])
        farm1_ids = {c["cycle_id"] for c in farm1}
        v.check("filtro FARM-001 agrupa C1 e alias C3", farm1_ids == {"C1", "C3"}, str(farm1_ids))
        farm2 = filter_by_selected_properties(cycles, ["FARM-002"])
        v.check("filtro 1 ID reduz", len(farm2) == 1 and farm2[0]["cycle_id"] == "C2")
        two = filter_by_selected_properties(cycles, ["FARM-001", "FARM-002"])
        v.check("filtro 2 IDs faz união", len(two) == 3, str(len(two)))

        index = build_pipeline_run_index(cycles)
        v.check(
            "índice pipeline mapeia run_id",
            index.get("R1") == "FARM-001" and index.get("R2") == "FARM-002",
        )

        events = [
            {"event_type": "RAW_REGISTERED", "pipeline_run_id": "R1"},
            {"event_type": "CALC_DONE", "pipeline_execution_id": "R2"},
            {"event_type": "OTHER", "payload_json": {"cycle_id": "C1"}},
        ]
        filtered = filter_provenance_events(events, cycles, ["FARM-001"])
        v.check("eventos filtrados por pipeline", len(filtered) == 2, f"len={len(filtered)}")
        v.check("eventos filtro vazio = todos", len(filter_provenance_events(events, cycles, [])) == 3)

        # Labels: validados separadamente dos IDs, sobre catálogo isolado
        v.check("rótulo todas", get_selected_property_label([], catalog) == "Todas as propriedades")
        v.check(
            "rótulo 2 props",
            get_selected_property_label(["FARM-001", "FARM-002"], catalog) == "2 propriedades selecionadas",
        )
        label_one = get_selected_property_label(["FARM-001"], catalog)
        v.check("rótulo 1 prop não vazio", bool(label_one) and label_one != "FARM-001", label_one)
        v.check(
            "rótulo 1 prop = nome do catálogo isolado",
            "Santa Clara" in label_one,
            label_one,
        )
        # Explicitamente: NÃO depender de "Embrapa P-1"
        v.check(
            "rótulo não depende de Embrapa P-1",
            "Embrapa" not in label_one,
            label_one,
        )

        title = format_page_title("Dashboard", ["FARM-001"], catalog)
        v.check("título com sufixo", title.startswith("Dashboard — "), title)
        v.check("título sem filtro", format_page_title("Dashboard", [], catalog) == "Dashboard")

        metrics = aggregate_calculation_metrics(two)
        v.check(
            "agregação soma co2e",
            abs(metrics["co2e_total_kg"] - 350.0) < 1e-6,
            str(metrics["co2e_total_kg"]),
        )
        v.check(
            "agregação soma by_source",
            abs(metrics["by_source"].get("enteric", 0) - 100.0) < 1e-6,
        )

        grouped = aggregate_by_property(cycles)
        v.check(
            "aggregate_by_property chaves",
            {"FARM-001", "FARM-002"}.issubset(grouped.keys()),
            str(list(grouped.keys())),
        )
        v.check(
            "aggregate_by_property FARM-001",
            len(grouped.get("FARM-001", [])) == 2,
            str(len(grouped.get("FARM-001", []))),
        )
        v.check("aggregate_by_property FARM-002", len(grouped.get("FARM-002", [])) == 1)

        real_nested = {
            "cycle_id": "REAL",
            "property_id": "FARM-001",
            "raw_file": {"property_id": "FARM-REAL"},
        }
        real_ids = get_all_property_ids(real_nested)
        v.check(
            "get_all_property_ids topo + raw_file",
            "FARM-001" in real_ids and "FARM-REAL" in real_ids,
            str(real_ids),
        )

        test_only_raw = {"raw_file": {"property_id": "FARM-TEST"}}
        v.check(
            "get_all_property_ids só raw_file",
            get_all_property_ids(test_only_raw) == {"FARM-TEST"},
            str(get_all_property_ids(test_only_raw)),
        )

    return print_structured_summary(v, "Property filter validation")


if __name__ == "__main__":
    raise SystemExit(main())
