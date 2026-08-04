"""Valida fonte ontológica de domínio + ausência de yearly em novos dados."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "agrotrace-carbon-ontology-manager"))
sys.path.insert(0, str(REPO / "agrotrace-carbon-calculation-service"))


def main() -> int:
    errors: list[str] = []

    def check(cond: bool, msg: str) -> None:
        if not cond:
            errors.append(msg)
            print(f"  FAIL: {msg}")
        else:
            print(f"  OK:   {msg}")

    from emissions.temporal_scope import TemporalScope, normalize_temporal_label

    check(normalize_temporal_label("yearly") is TemporalScope.ANNUAL, "yearly->ANNUAL na leitura")
    check(TemporalScope.ANNUAL.value == "annual", "ANNUAL.value == annual")
    check(TemporalScope.ANNUAL.value != "yearly", "nao grava yearly")

    from ontology import build_full_ontology
    from ontology.cycle_model import normalize_granularity, upsert_emission_cycle, upsert_property
    from ontology.result_lifecycle import upsert_emission_result, list_active_results
    from ontology.query_service import get_emission_summary

    onto = build_full_ontology()
    upsert_property(onto, property_id="P-VAL", name="Validação")
    upsert_emission_cycle(
        onto,
        cycle_id="VAL-1",
        property_id="P-VAL",
        reporting_period="2022",
        temporal_granularity="yearly",  # alias → annual
        status="PendingApproval",
    )
    check(normalize_granularity("yearly") == "annual", "normalize yearly->annual")
    upsert_emission_result(
        onto,
        cycle_id="VAL-1",
        property_id="P-VAL",
        reporting_period="2022",
        temporal_granularity="annual",
        formula_id="total_ghg",
        gas="CO2e",
        value=1000.0,
        unit="kg CO2e",
        co2e_value=1000.0,
        emission_source="total",
        status="preliminary",
    )
    rows = list_active_results(onto, "VAL-1")
    check(len(rows) == 1, "um resultado ativo")
    check(rows[0]["temporal_granularity"] == "annual", "resultado gravado como annual")
    summary = get_emission_summary(onto, "VAL-1")
    check(summary["source"] == "ontology", "summary.source=ontology")
    check(summary["co2e_total_kg"] == 1000.0, "summary co2e relido")

    # Arquitetural: view services de dominio nao devem importar MOCK_PROPERTIES
    forbidden_hits = []
    for path in (ROOT / "services").glob("*_view_service.py"):
        text = path.read_text(encoding="utf-8")
        if "MOCK_PROPERTIES" in text:
            forbidden_hits.append(path.name)
    for path in (
        ROOT / "services" / "indicator_aggregation_service.py",
        ROOT / "services" / "emission_detail_service.py",
        ROOT / "services" / "dashboard_service.py",
    ):
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if "from emissions.defaults" in text:
                forbidden_hits.append(path.name + ":defaults")
    check(not forbidden_hits, f"sem MOCK/defaults em view domain ({forbidden_hits})")

    if errors:
        print(f"\n{len(errors)} falha(s)")
        return 1
    print("\nvalidate_ontology_domain_source OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
