"""Aceite ponta a ponta: pending → corrected (OWL) → recalc → confirmed → publish → reboot.

Critérios:
- Default enteric Lactating_Cows = 100 (anual) catalogado como pending
- Edição para 120 persiste na ontologia com status corrected
- Recálculo lê factor_catalog (não override solto da UI)
- Confirmação marca confirmed; reboot recupera valor/status do catalog
- Publicação marca published e aponta manifesto para OWL final
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(REPO / "agrotrace-carbon-calculation-service"))
sys.path.insert(0, str(REPO / "agrotrace-carbon-ontology-manager"))

from services import ontology_runtime_cache as onto_cache  # noqa: E402
from services.calculation_approval_service import (  # noqa: E402
    approve_item,
    apply_factor_edits,
    can_finalize,
)
from services.calculation_review_service import build_calculation_review  # noqa: E402
from services.ontology_adapter import (  # noqa: E402
    get_onto_for_cycle,
    publish_to_canonical_model,
)
from services.publication_service import publish_approved_cycle  # noqa: E402
from services import local_orchestrator  # noqa: E402


EMBRAPA_P9_2021_11 = {
    "property_id": "P-9",
    "milk_production": 4039.0,
    "milk_sales": 4039.0,
    "number_of_lactating_cows": 13.0,
    "reproducers": 2.0,
    "lactating_cows": 13.0,
    "dry_cows": 3.0,
    "pregnant_heifers": 0.0,
    "heifers_in_raising": 9.0,
    "suckling_calves_female": 1.0,
    "suckling_calves_male": 0.0,
    "male_calves_in_raising": 0.0,
    "male_calves_in_fattening": 0.0,
    "draft_and_breeding_bulls": 0.0,
    "number_of_dry_cows": 13.0,
    "period_start": "2021-11-01",
    "period_end": "2021-11-30",
    "_temporal_context": {
        "type": "interval",
        "start": "2021-11-01",
        "end": "2021-11-30",
        "granularity": "month",
    },
}


def _check(cond: bool, msg: str, errors: list[str]) -> None:
    if not cond:
        errors.append(msg)
        print(f"  FAIL: {msg}")
    else:
        print(f"  OK:   {msg}")


def _find_item(cycle: dict, formula_id: str) -> dict:
    for it in (cycle.get("calculation_review") or {}).get("items") or []:
        if it.get("formula_id") == formula_id:
            return it
    raise RuntimeError(f"Item {formula_id} não encontrado na revisão")


def main() -> int:
    errors: list[str] = []
    print("=== validate_ontology_parameter_lifecycle ===")

    onto_cache.clear()
    cycle_id = "TEST-ONTO-LIFECYCLE-P9"
    cycle: dict = {
        "cycle_id": cycle_id,
        "property_id": "P-9",
        "property_name": "Embrapa P-9",
        "reporting_period": "2021-11",
        "frequency": "monthly",
        "granularity": "monthly",
        "normalized_data": [EMBRAPA_P9_2021_11],
        "wrapper": {"layout_id": "monthly:v1"},
        "steps": {
            "ontology": {"status": "DONE"},
            "semantic": {"status": "DONE"},
        },
        "semantic_validation": {
            "critical_errors": 0,
            "warnings": 0,
            "status": "SEMANTIC_VALIDATION_APPROVED",
        },
        "errors": [],
    }

    # ── A: populate + pending ───────────────────────────────────────────────
    print("\n[A] populate ontology (pending)")
    ontology_result = publish_to_canonical_model({
        "normalized_payload": [EMBRAPA_P9_2021_11],
        "layout_id": "monthly:v1",
        "cycle_id": cycle_id,
    })
    cycle["ontology"] = {k: v for k, v in ontology_result.items() if k != "_ontology"}
    if ontology_result.get("_ontology") is not None:
        onto_cache.set_ontology(cycle_id, ontology_result["_ontology"])

    catalog = (cycle.get("ontology") or {}).get("factor_catalog") or {}
    enteric = catalog.get("enteric_ch4_kg_per_animal") or {}
    statuses = (catalog.get("_statuses") or {}).get("enteric_ch4_kg_per_animal") or {}
    _check(
        enteric.get("Lactating_Cows") == 100.0,
        f"default Lactating_Cows=100 (obtido {enteric.get('Lactating_Cows')})",
        errors,
    )
    _check(
        statuses.get("Lactating_Cows") == "pending",
        f"status pending (obtido {statuses.get('Lactating_Cows')})",
        errors,
    )

    # ── cálculo preliminar ──────────────────────────────────────────────────
    print("\n[A2] preliminary calc from catalog")
    cycle = local_orchestrator.run_calculation_step(cycle, {"temporal_scope": "monthly"})
    calc = cycle.get("calculation") or {}
    factors_used = calc.get("factors_used") or {}
    enteric_used = factors_used.get("enteric_ch4_kg_per_animal") or {}
    expected_monthly = 100.0 / 12.0
    got = enteric_used.get("Lactating_Cows")
    _check(
        got is not None and abs(float(got) - expected_monthly) < 1e-9,
        f"prelim enteric mensal~={expected_monthly:.6f} (obtido {got})",
        errors,
    )
    sources = calc.get("factor_sources") or {}
    _check(
        sources.get("enteric_ch4_kg_per_animal") in {"ontology", "defaults"},
        f"fonte enteric={sources.get('enteric_ch4_kg_per_animal')}",
        errors,
    )

    cycle["calculation_review"] = build_calculation_review(cycle)
    enteric_item = _find_item(cycle, "enteric_fermentation_ch4")

    # ── B: correção → OWL corrected → recalc ───────────────────────────────
    print("\n[B] edit → ontology corrected → recalc")
    cycle = apply_factor_edits(
        cycle,
        enteric_item["calculation_item_id"],
        edits=[{
            "group": "enteric_ch4_kg_per_animal",
            "factor_key": "Lactating_Cows",
            "value": 120.0,
        }],
        reviewer="Tester",
        methodology="IPCC AR4 edited for acceptance",
        factors_changed=True,
    )
    catalog = (cycle.get("ontology") or {}).get("factor_catalog") or {}
    enteric = catalog.get("enteric_ch4_kg_per_animal") or {}
    statuses = (catalog.get("_statuses") or {}).get("enteric_ch4_kg_per_animal") or {}
    _check(enteric.get("Lactating_Cows") == 120.0, "catalog Lactating_Cows=120", errors)
    _check(statuses.get("Lactating_Cows") == "corrected", "status corrected", errors)
    _check(
        "enteric_ch4_kg_per_animal" not in (cycle.get("calculation_params") or {}),
        "sem override numerico em calculation_params",
        errors,
    )

    calc = cycle.get("calculation") or {}
    enteric_used = (calc.get("factors_used") or {}).get("enteric_ch4_kg_per_animal") or {}
    expected_monthly = 120.0 / 12.0
    got = enteric_used.get("Lactating_Cows")
    _check(
        got is not None and abs(float(got) - expected_monthly) < 1e-9,
        f"recalc enteric mensal~={expected_monthly:.6f} (obtido {got})",
        errors,
    )
    sources = calc.get("factor_sources") or {}
    _check(
        sources.get("enteric_ch4_kg_per_animal") == "ontology",
        f"recalc fonte=ontology (obtido {sources.get('enteric_ch4_kg_per_animal')})",
        errors,
    )

    # ── C: confirmar todos os itens ─────────────────────────────────────────
    print("\n[C] confirm parameters via approve_item")
    review = build_calculation_review(cycle, preserve_decisions=True)
    cycle["calculation_review"] = review
    for it in review.get("items") or []:
        st = it.get("status")
        if st in {"APPROVED", "NOT_APPLICABLE"}:
            continue
        # Após edit, enteric fica ADJUSTMENT_PENDING_RECALCULATION — aprovar
        cycle = approve_item(
            cycle,
            it["calculation_item_id"],
            reviewer="Tester",
            justification="Aceite lifecycle",
        )

    catalog = (cycle.get("ontology") or {}).get("factor_catalog") or {}
    statuses = (catalog.get("_statuses") or {}).get("enteric_ch4_kg_per_animal") or {}
    _check(statuses.get("Lactating_Cows") == "confirmed", "status confirmed", errors)
    ok, msg = can_finalize(cycle)
    _check(ok, f"can_finalize ({msg})", errors)

    # ── reboot: limpa cache, reconstrói do catalog ──────────────────────────
    print("\n[C2] reboot from factor_catalog")
    onto_cache.clear()
    onto = get_onto_for_cycle(cycle)
    from ontology.parameter_lifecycle import extract_factor_catalog_with_statuses

    rebuilt = extract_factor_catalog_with_statuses(onto) or {}
    _check(
        (rebuilt.get("enteric_ch4_kg_per_animal") or {}).get("Lactating_Cows") == 120.0,
        "reboot OWL Lactating_Cows=120",
        errors,
    )
    _check(
        ((rebuilt.get("_statuses") or {}).get("enteric_ch4_kg_per_animal") or {}).get("Lactating_Cows")
        == "confirmed",
        "reboot status confirmed",
        errors,
    )

    # ── D: publicação final ─────────────────────────────────────────────────
    print("\n[D] publish final OWL + manifesto")
    cycle["approval"] = {
        "decision": "APPROVED",
        "approver": "Tester",
        "approved_at": "2026-07-22T12:00:00",
        "justification": "Aceite",
    }
    # publish_approved_cycle marca published + manifesto
    pub = publish_approved_cycle(cycle)
    cycle["publication"] = pub

    catalog = (cycle.get("ontology") or {}).get("factor_catalog") or {}
    statuses = (catalog.get("_statuses") or {}).get("enteric_ch4_kg_per_animal") or {}
    _check(statuses.get("Lactating_Cows") == "published", "status published", errors)
    _check(bool(pub.get("ontology_ref")), f"ontology_ref={pub.get('ontology_ref')}", errors)
    _check(
        pub.get("ontology_ref") and "_final" in str(pub.get("ontology_ref")),
        "ontology_ref aponta OWL final",
        errors,
    )
    _check(
        (pub.get("emission_factors") or {}).get("enteric_ch4_kg_per_animal", {}).get("Lactating_Cows")
        in (120.0 / 12.0, 120.0)
        or abs(
            float(
                (pub.get("emission_factors") or {})
                .get("enteric_ch4_kg_per_animal", {})
                .get("Lactating_Cows", 0)
            )
            - (120.0 / 12.0)
        )
        < 1e-9,
        "manifesto emission_factors contém 120/12",
        errors,
    )
    owl_path = Path((cycle.get("ontology") or {}).get("export_paths", {}).get("owl") or "")
    _check(owl_path.is_file(), f"OWL final existe: {owl_path}", errors)

    print()
    if errors:
        print(f"FAILED ({len(errors)} errors)")
        return 1
    print("PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
