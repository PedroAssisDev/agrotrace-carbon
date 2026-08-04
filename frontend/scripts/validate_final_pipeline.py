"""Validação final da pipeline completa — upload até verificação de integridade.

Uso:
    cd frontend
    python scripts/validate_final_pipeline.py
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

import config  # noqa: E402
from services import cycle_state, local_orchestrator as orch  # noqa: E402
from services.blockchain_view_service import is_blockchain_unlocked  # noqa: E402
from services.bootstrap import bootstrap_all  # noqa: E402
from services.calculation_approval_service import (  # noqa: E402
    approve_item,
    approve_with_zero,
    can_finalize,
    finalize_file_approval,
)
from services.calculation_review_service import (  # noqa: E402
    build_calculation_review,
    ensure_calculation_review,
    list_review_items,
    MANDATORY_FORMULAS,
)
from services.cycle_status_service import resolve_managerial_status, traceability_summary  # noqa: E402
from services.provenance_event_catalog import canonical_event_type  # noqa: E402
from utils.file_helpers import get_cycle, save_cycle  # noqa: E402
from utils.formatting import (  # noqa: E402
    format_count,
    format_hash_short,
    format_intensity_kg_co2e_per_l,
    format_kg_co2e,
    format_percent,
    format_t_co2e,
)
from utils.hash_helpers import sha256_file  # noqa: E402

SAMPLE_CSV = config.SAMPLE_DATA_DIR / "monthly_report.csv"

MIN_EVENTS = {
    "RAW_DATA_REGISTERED",
    "ORIGINAL_FILE_STORED",
    "WRAPPER_EXECUTED",
    "NORMALIZED_BATCH_CREATED",
    "CANONICAL_MODEL_POPULATED",
    "SEMANTIC_VALIDATION_COMPLETED",
    "CALCULATION_EXECUTED",
    "PRELIMINARY_RESULT_CREATED",
    "HUMAN_APPROVAL_REQUESTED",
    "CALCULATION_APPROVED",
    "FINAL_ONTOLOGY_PUBLISHED",
    "EVIDENCE_PACKAGE_CREATED",
    "MERKLE_ROOT_CREATED",
    "ANCHORING_SIMULATED",
    "INTEGRITY_VERIFICATION_EXECUTED",
    "PROVENANCE_CHAIN_VERIFIED",
}


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


def _event_types(cycle: dict) -> set[str]:
    raw = {e.get("event_type") for e in (cycle.get("provenance_events") or [])}
    return raw | {canonical_event_type(t) for t in raw if t}


def _has_event(cycle: dict, *names: str) -> bool:
    types = _event_types(cycle)
    for name in names:
        if name in types or canonical_event_type(name) in types:
            return True
    return False


def _approve_all_items(cycle: dict) -> dict:
    cycle = ensure_calculation_review(cycle)
    for it in list_review_items(cycle):
        if it.get("zero_assumptions"):
            cycle = approve_with_zero(cycle, it["calculation_item_id"], reviewer="Validator")
        else:
            cycle = approve_item(cycle, it["calculation_item_id"], reviewer="Validator")
    return cycle


def main() -> int:
    v = Validator()
    print("=== validate_final_pipeline ===\n")

    bootstrap_all()
    if not SAMPLE_CSV.exists():
        v.check("01 CSV de amostra disponível", False, str(SAMPLE_CSV))
        return 1 if v.errors else 0

    from utils.file_helpers import save_raw_file

    raw = save_raw_file(
        SAMPLE_CSV,
        property_id="FARM-FINAL-AUDIT",
        reporting_period="2026-06",
        original_filename="monthly_report.csv",
    )
    v.check("02 upload cria metadados de arquivo bruto", bool(raw.get("stored_path") and raw.get("sha256")))
    v.check("03 arquivo bruto salvo em raw_originals", Path(raw["stored_path"]).exists())
    v.check(
        "04 hash SHA-256 do arquivo salvo",
        raw.get("sha256") == sha256_file(raw["stored_path"]),
    )

    cycle = orch.run_auto_pipeline_after_ingestion(
        raw,
        property_id="FARM-FINAL-AUDIT",
        property_name="Fazenda Auditoria Final",
        reporting_period="2026-06",
    )
    cycle_id = cycle.get("cycle_id")
    v.check("05 upload cria ciclo JSON", bool(cycle_id))
    v.check("06 ciclo persistido em data/cycles", (config.CYCLES_DIR / f"{cycle_id}.json").exists())

    v.check("07 wrapper executado após arquivo salvo", _has_event(cycle, "WRAPPER_EXECUTED"))
    v.check("08 lote normalizado criado", bool(cycle.get("normalized_data") or cycle.get("wrapper", {}).get("normalized_file")))
    v.check("09 ontologia populada", _has_event(cycle, "CANONICAL_MODEL_POPULATED", "CANONICAL_PUBLISHED"))
    v.check("10 validação semântica executada", _has_event(cycle, "SEMANTIC_VALIDATION_COMPLETED"))
    v.check("11 cálculo preliminar gerado", bool(cycle.get("calculation")))
    v.check("12 status aguardando aprovação humana", cycle.get("current_status") == "AWAITING_HUMAN_APPROVAL")
    v.check("13 blockchain bloqueado após ingestão", not is_blockchain_unlocked(cycle))
    v.check("14 sem pacote de evidências após ingestão", not cycle.get("evidence_package"))

    review = build_calculation_review(cycle)
    v.check("15 calculation_review criável", bool(review.get("file_review_id")))
    items = review.get("items") or []
    v.check("16 cada cálculo obrigatório vira item revisável", len(items) >= len(MANDATORY_FORMULAS))

    zero_items = [it for it in items if it.get("zero_assumptions")]
    if zero_items:
        try:
            approve_item(cycle, zero_items[0]["calculation_item_id"], reviewer="Validator")
            v.check("17 zero assumido exige confirmação", False)
        except ValueError:
            v.check("17 zero assumido exige confirmação", True)
    else:
        v.check("17 zero assumido exige confirmação (sem zero na amostra)", True)

    partial = ensure_calculation_review(copy.deepcopy(cycle))
    ok_part, _ = can_finalize(partial)
    v.check("18 aprovação final bloqueia com cálculo pendente", not ok_part)

    ready = _approve_all_items(copy.deepcopy(cycle))
    ok_all, msg_all = can_finalize(ready)
    v.check("19 aprovação final libera com todos decididos", ok_all, msg_all)

    pre_pub_unlocked = is_blockchain_unlocked(ready)
    v.check("20 publicação final só após aprovação (pré-finalize)", not pre_pub_unlocked)

    try:
        final = finalize_file_approval(ready, reviewer="Validator", justification="Auditoria final")
    except Exception as exc:
        v.check("21 finalize_file_approval executa", False, str(exc))
        final = ready

    v.check("22 publicação final ocorre após aprovação", _has_event(final, "FINAL_ONTOLOGY_PUBLISHED"))
    v.check("23 blockchain liberado após publicação final", is_blockchain_unlocked(final))
    v.check("24 pacote de evidências criado", bool(final.get("evidence_package")))
    ep = final.get("evidence_package") or {}
    hashes = ep.get("hashes") or final.get("hashes") or {}
    v.check("25 evidência contém hashes", bool(hashes))
    v.check("26 Merkle Root gerada", bool(ep.get("merkle_root")))
    v.check("27 integridade verificada", bool(final.get("integrity")))

    missing_events = sorted(MIN_EVENTS - _event_types(final))
    v.check("28 proveniência possui eventos mínimos", len(missing_events) == 0, ", ".join(missing_events))

    st = resolve_managerial_status(final)
    trace = traceability_summary(final)
    v.check("29 status gerencial não mostra evidência sem gate", not trace["evidence_generated"] or is_blockchain_unlocked(final))
    v.check("30 status oficial após verificação", st.key in ("integrity_verified", "evidence_generated", "published"))

    v.check("31 format_t_co2e", "t CO₂e" in format_t_co2e(1.5))
    v.check("32 format_kg_co2e", "kg CO₂e" in format_kg_co2e(100))
    v.check("33 format_intensity_kg_co2e_per_l", "kg CO₂e/L" in format_intensity_kg_co2e_per_l(0.5))
    v.check("34 format_percent", format_percent(12.3).endswith("%"))
    v.check("35 format_count", format_count(1234) == "1.234")
    v.check("36 format_hash_short", len(format_hash_short("a" * 64)) <= 16)

    save_cycle(final)
    reloaded = get_cycle(cycle_id)
    v.check("37 ciclo recarregado após finalização", bool(reloaded and reloaded.get("evidence_package")))

    print(f"\n--- {len(v.ok)} OK, {len(v.errors)} FAIL ---")
    return 1 if v.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
