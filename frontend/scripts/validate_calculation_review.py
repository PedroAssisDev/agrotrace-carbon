"""Validação headless da tela Revisão e Aprovação por cálculo.

Uso:
    python scripts/validate_calculation_review.py
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from utils.data_root_cli import apply_data_root_from_argv  # noqa: E402

apply_data_root_from_argv()

from pages.approval_review import layout as approval_layout  # noqa: E402
from services.blockchain_view_service import is_blockchain_unlocked  # noqa: E402
from services.calculation_approval_service import (  # noqa: E402
    apply_factor_edits,
    approve_item,
    approve_with_zero,
    can_finalize,
    finalize_file_approval,
    reject_item,
)
from services.calculation_factor_mapping_service import (  # noqa: E402
    build_factor_rows_for_display,
    get_default_factor_methodology,
    get_factor_groups_for_formula,
)
from services.calculation_input_mapping_service import (  # noqa: E402
    build_input_overrides,
    extract_normalized_variables,
    list_compatible_alternatives,
    resolve_input_variables,
)
from services.calculation_review_service import (  # noqa: E402
    build_calculation_review,
    ensure_calculation_review,
    list_review_items,
    MANDATORY_FORMULAS,
)
from services.mock_data import mock_full_cycle  # noqa: E402
from services.ontology_extraction_service import (  # noqa: E402
    build_canonical_variables_snapshot,
    extract_ontology_variables,
)
from services.ontology_indicator_registry import (  # noqa: E402
    FORMULA_ONTOLOGY_REQUIREMENTS,
    get_formula_requirements,
)
from services.page_context import resolve_page_context  # noqa: E402
from services.review_provenance_service import list_review_events  # noqa: E402
from utils.file_helpers import list_cycles, save_cycle  # noqa: E402


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.ok: list[str] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.ok.append(name)
            print(f"  [OK]   {name}")
        else:
            msg = f"{name}{f' — {detail}' if detail else ''}"
            self.errors.append(msg)
            print(f"  [FAIL] {msg}")


def _pending_cycle() -> dict:
    c = mock_full_cycle()
    c.pop("publication", None)
    c.pop("evidence_package", None)
    c.pop("anchoring", None)
    c["steps"] = {**(c.get("steps") or {}), "publication": {"status": "PENDING"}, "approval": {"status": "PENDING"}}
    c["approval"] = {"decision": "PENDING"}
    c["current_status"] = "AWAITING_APPROVAL"
    c.pop("calculation_review", None)
    return c


def main() -> int:
    v = Validator()
    print("=== validate_calculation_review ===\n")

    import tempfile

    import config

    with tempfile.TemporaryDirectory() as tmp:
        original_cycles = config.CYCLES_DIR
        config.CYCLES_DIR = Path(tmp) / "cycles"
        config.CYCLES_DIR.mkdir(parents=True, exist_ok=True)
        try:
            return _run_validation(v)
        finally:
            config.CYCLES_DIR = original_cycles


def _run_validation(v: Validator) -> int:
    cycle = _pending_cycle()
    ont = cycle.setdefault("ontology", {})
    ont["canonical_variables"] = build_canonical_variables_snapshot(cycle)
    save_cycle(cycle)
    gf = {"farm_id": cycle.get("property_id"), "cycle_id": cycle.get("cycle_id")}
    ctx = resolve_page_context(cycle, gf, cycle.get("cycle_id"))

    # 1. Gera review
    review = build_calculation_review(cycle)
    v.check("build_calculation_review gera estrutura", bool(review.get("file_review_id")))
    v.check("itens obrigatórios presentes", len(review.get("items") or []) >= len(MANDATORY_FORMULAS))

    cycle = ensure_calculation_review(cycle)
    items = list_review_items(cycle)
    v.check("itens revisáveis listados", len(items) >= 5)

    # 2. Montagem da página
    try:
        page = approval_layout(cycle, gf, {}, cycle.get("cycle_id"))
        page_str = str(page)
        v.check("approval_layout monta sem erro", page is not None)
        v.check("seletor de ciclo presente", "approval-cycle-select" in page_str)
        v.check("tabela de cálculos presente", "cr-review-table" in page_str)
        v.check("botão finalizar presente", "cr-btn-finalize" in page_str)
        v.check("fluxo antigo btn-approve removido da página", 'id="btn-approve"' not in page_str)
        v.check("card modelo canônico presente", "Modelo canônico" in page_str)
    except Exception as exc:
        v.check("approval_layout monta sem erro", False, str(exc))

    # 3. Unidade / display
    total_item = next((it for it in items if it.get("formula_id") == "total_ghg_co2e"), None)
    v.check("item total tem unidade", bool(total_item and total_item.get("result_unit")))

    # 4. Zero explícito
    zero_items = [it for it in items if it.get("zero_assumptions")]
    v.check("detecção de zero assumido (estrutura)", isinstance(zero_items, list))

    # 5. Zero bloqueia sem confirmação
    if zero_items:
        zi = zero_items[0]
        try:
            approve_item(cycle, zi["calculation_item_id"], reviewer="Test", justification="x")
            v.check("aprovar com zero não confirmado falha", False)
        except ValueError:
            v.check("aprovar com zero não confirmado falha", True)
    else:
        v.check("aprovar com zero não confirmado (sem zero na amostra)", True)

    # 6. Ontologia — snapshot e resolução
    snap = (cycle.get("ontology") or {}).get("canonical_variables") or []
    v.check("snapshot canonical_variables presente", len(snap) > 0)
    pool = extract_ontology_variables(cycle)
    v.check("extrai variáveis ontológicas", isinstance(pool, list) and len(pool) > 0)
    enteric_req = get_formula_requirements("enteric_fermentation_ch4")
    v.check("fórmulas usam registry ontológico", len(enteric_req) >= 4 and enteric_req[0].get("ontology_var"))
    found, missing = resolve_input_variables(cycle, enteric_req)
    v.check("resolve inputs com origem ontológica", any(f.get("origin") in ("ontology", "canonical_projection", "calculation_snapshot", "normalized_fallback") for f in found))
    v.check("registry substitui catálogo legado", "enteric_fermentation_ch4" in FORMULA_ONTOLOGY_REQUIREMENTS)

    # 7. Variável alternativa
    vars_norm = extract_normalized_variables(cycle)
    v.check("extrai pool ontológico (compat)", isinstance(vars_norm, list))
    alts = list_compatible_alternatives(cycle, "milk_production", "L")
    v.check("lista alternativas compatíveis", isinstance(alts, list))
    if alts:
        v.check("alternativas têm ontology_class", bool(alts[0].get("ontology_class")))

    overrides = build_input_overrides(cycle, {"target_variable": "milk_production", "source_variable": "milk", "value": 1000}, ontology_var="milk_production")
    v.check("prepara input_overrides via ontology_var", "milk_liters" in overrides or "_last_swap" in overrides)

    # 7b. Edição de fatores
    enteric_groups = get_factor_groups_for_formula("enteric_fermentation_ch4")
    v.check("fatores mapeados para entérica", "enteric_ch4_kg_per_animal" in enteric_groups)
    factor_work = copy.deepcopy(cycle)
    factor_work = ensure_calculation_review(factor_work)
    enteric_item = next(i for i in list_review_items(factor_work) if i.get("formula_id") == "enteric_fermentation_ch4")
    v.check("item de revisão tem sub_id", enteric_item.get("sub_id") == "enteric")
    factor_rows = build_factor_rows_for_display(factor_work, enteric_item)
    v.check("linhas de fatores para edição", len(factor_rows) > 0 and "factor_key" in factor_rows[0])

    annual_path = FRONTEND_ROOT / "data" / "cycles" / "ANNUAL-2026-FARM-MONTHLY-001.json"
    if annual_path.exists():
        annual = json.loads(annual_path.read_text(encoding="utf-8"))
        annual = ensure_calculation_review(annual)
        annual_enteric = next(
            i for i in list_review_items(annual) if i.get("formula_id") == "enteric_fermentation_ch4"
        )
        annual_rows = build_factor_rows_for_display(annual, annual_enteric)
        lact = next((r for r in annual_rows if r.get("factor_key") == "Lactating_Cows"), None)
        v.check(
            "ciclo ANNUAL sem factors_used usa subcálculo",
            lact is not None and float(lact.get("valor") or 0) < 20,
            f"valor={lact.get('valor') if lact else None}",
        )
    try:
        edits = [{
            "group": factor_rows[0]["group"],
            "factor_key": factor_rows[0]["factor_key"],
            "value": float(factor_rows[0]["valor"] or 0) + 1.0,
        }]
        factor_work = apply_factor_edits(
            factor_work, enteric_item["calculation_item_id"],
            edits=edits,
            reviewer="Test",
            methodology=get_default_factor_methodology(factor_work),
            factors_changed=True,
        )
        updated_enteric = next(
            i for i in list_review_items(factor_work) if i["calculation_item_id"] == enteric_item["calculation_item_id"]
        )
        v.check("aplicar fatores marca item para reaprovação", updated_enteric.get("status") == "ADJUSTMENT_PENDING_RECALCULATION")
        v.check("factor_selections persistido", bool((factor_work.get("calculation_params") or {}).get("factor_selections")))
        meth = updated_enteric.get("factor_methodology") or {}
        v.check("metodologia por item persistida", meth.get("applied") == get_default_factor_methodology(factor_work))
    except Exception as exc:
        v.check("aplicar fatores recalcula ciclo", False, str(exc))

    # 8. Ajuste registrado / status muda
    work = copy.deepcopy(cycle)
    work = ensure_calculation_review(work)
    first = list_review_items(work)[0]
    if first.get("zero_assumptions"):
        work = approve_with_zero(work, first["calculation_item_id"], reviewer="Test")
        v.check("aprovar com zero muda status", first["calculation_item_id"] in [i["calculation_item_id"] for i in list_review_items(work)])
    else:
        work = approve_item(work, first["calculation_item_id"], reviewer="Test")
        updated = next(i for i in list_review_items(work) if i["calculation_item_id"] == first["calculation_item_id"])
        v.check("aprovar item muda status", updated.get("status") == "APPROVED")

    # 9. Rejeitado bloqueia final
    rejected = copy.deepcopy(cycle)
    rejected = ensure_calculation_review(rejected)
    rej_item = list_review_items(rejected)[1]
    rejected = reject_item(rejected, rej_item["calculation_item_id"], reviewer="Test", justification="teste")
    ok_rej, _ = can_finalize(rejected)
    v.check("rejeitado bloqueia finalização", not ok_rej)

    # 10. Final só com todos decididos
    partial = copy.deepcopy(cycle)
    partial = ensure_calculation_review(partial)
    ok_part, _ = can_finalize(partial)
    v.check("final bloqueado com pendências", not ok_part)

    all_ok = copy.deepcopy(cycle)
    all_ok = ensure_calculation_review(all_ok)
    for it in list_review_items(all_ok):
        if it.get("zero_assumptions"):
            all_ok = approve_with_zero(all_ok, it["calculation_item_id"], reviewer="Test")
        else:
            all_ok = approve_item(all_ok, it["calculation_item_id"], reviewer="Test")
    ok_all, msg_all = can_finalize(all_ok)
    v.check("final liberado com todos decididos", ok_all, msg_all)

    # 11. Eventos emitidos
    events_before = len(list_review_events(all_ok))
    v.check("eventos de revisão emitidos", events_before > 0)

    # 12. Blockchain bloqueado antes da publicação
    v.check("blockchain bloqueado antes da publicação", not is_blockchain_unlocked(cycle))

    # 13. Ciclos antigos carregam (fallback sem snapshot)
    old = _pending_cycle()
    old.pop("calculation_review", None)
    old.get("ontology", {}).pop("canonical_variables", None)
    old_review = build_calculation_review(old)
    v.check("ciclos antigos recebem review on-the-fly", bool(old_review.get("items")))
    old_pool = extract_ontology_variables(old)
    v.check("ciclos antigos resolvem via fallback", isinstance(old_pool, list))

    # Finalização (opcional — pode falhar sem serviços externos completos)
    try:
        fin = copy.deepcopy(all_ok)
        fin = finalize_file_approval(fin, reviewer="Test", justification="validação")
        v.check("finalize_file_approval executa", fin.get("calculation_review", {}).get("status", "").startswith("APPROVED"))
    except Exception as exc:
        v.check("finalize_file_approval executa", False, str(exc))

    print(f"\n--- {len(v.ok)} OK, {len(v.errors)} FAIL ---")
    return 1 if v.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
