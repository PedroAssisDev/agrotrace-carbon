"""Validação headless do pipeline do frontend AgroTrace Carbon.

Executa o fluxo automático pós-ingestão até pendência de aprovação
SEM navegador. Não auto-aprova nem gera evidências/blockchain.

Uso:
    python scripts/validate_frontend_pipeline.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

import config  # noqa: E402
from utils.data_root_cli import apply_data_root_from_argv  # noqa: E402

apply_data_root_from_argv()

from services import cycle_state, local_orchestrator as orch  # noqa: E402
from services.blockchain_view_service import is_blockchain_unlocked  # noqa: E402
from services.bootstrap import bootstrap_all  # noqa: E402
from services.cycle_status_service import resolve_managerial_status  # noqa: E402
from services.direct_imports import availability  # noqa: E402
from services.provenance_event_catalog import canonical_event_type  # noqa: E402
from utils.file_helpers import save_raw_file  # noqa: E402

SAMPLE_CSV = config.SAMPLE_DATA_DIR / "monthly_report.csv"


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.steps_ok: list[str] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.steps_ok.append(name)
            print(f"  [OK]   {name}")
        else:
            msg = f"{name}{f' — {detail}' if detail else ''}"
            self.errors.append(msg)
            print(f"  [FAIL] {msg}")


def _event_types(cycle: dict) -> set[str]:
    return {e.get("event_type") for e in (cycle.get("provenance_events") or [])}


def _has_event(cycle: dict, *names: str) -> bool:
    types = _event_types(cycle)
    canonical = {canonical_event_type(t) for t in types}
    for name in names:
        if name in types or canonical_event_type(name) in types or name in canonical:
            return True
    return False


def main() -> int:
    v = Validator()
    print("== AgroTrace Carbon — validação headless do pipeline automático (até pendência) ==\n")

    boot = bootstrap_all()
    v.check("01 bootstrap (paths/dbs)", all([boot.get("provenance_db"), boot.get("blockchain_db")]), str(boot))
    avail = availability()
    print(f"  Módulos reais: {avail}")

    if not SAMPLE_CSV.exists():
        v.check("CSV de amostra disponível", False, f"não encontrado: {SAMPLE_CSV}")
        return _finish(v)

    raw = save_raw_file(
        SAMPLE_CSV,
        property_id="FARM-MONTHLY-001",
        reporting_period="2026-05",
        original_filename="monthly_report.csv",
    )
    v.check("02 salvar arquivo bruto", Path(raw["stored_path"]).exists() and bool(raw["sha256"]))

    cycle = orch.run_auto_pipeline_after_ingestion(
        raw,
        property_id="FARM-MONTHLY-001",
        property_name="Fazenda Boa Vista Leiteira",
        reporting_period="2026-05",
        layout_name="monthly",
        layout_id="monthly:v1",
        uploaded_by="validate-script",
    )
    v.check("03 pipeline automática concluída", cycle.get("current_status") == "AWAITING_HUMAN_APPROVAL",
            f"status={cycle.get('current_status')}")
    v.check("04 etapa dados brutos", cycle_state.is_step_done(cycle, "raw_data"))
    v.check("05 pipeline_run registrado", bool(cycle.get("pipeline_run_id")))
    v.check("06 wrapper executado", cycle_state.is_step_done(cycle, "wrapper"),
            f"mode={cycle['steps']['wrapper'].get('mode')}")
    v.check(
        "07 lote normalizado",
        cycle_state.is_step_done(cycle, "normalization") and len(cycle.get("normalized_data", [])) > 0,
    )
    v.check("08 modelo canônico", cycle_state.is_step_done(cycle, "ontology"),
            f"mode={cycle['steps']['ontology'].get('mode')}")
    v.check(
        "09 validação semântica",
        cycle["steps"]["semantic"]["status"] in {"DONE", "DONE_WARNINGS"},
        f"status={cycle['steps']['semantic']['status']}",
    )
    v.check(
        "10 cálculo de emissões",
        cycle_state.is_step_done(cycle, "calculation")
        and (cycle.get("calculation") or {}).get("co2e_total_kg", 0) > 0,
        f"mode={cycle['steps']['calculation'].get('mode')}",
    )
    v.check("10b blockchain bloqueado após cálculo", not is_blockchain_unlocked(cycle))

    st = resolve_managerial_status(cycle)
    v.check("11 pendência de aprovação", st.key == "pending_approval", f"status={st.key}")
    v.check(
        "11b approval step aguardando",
        cycle["steps"]["approval"]["status"] == "AWAITING_APPROVAL",
    )
    v.check("11c sem decisão de aprovação", not (cycle.get("approval") or {}).get("decision"))
    v.check("11d publicação não realizada", (cycle.get("publication") or {}).get("status") == "NotPublished")
    v.check("11e sem pacote de evidência", not cycle.get("evidence_package"))
    v.check("11f blockchain ainda bloqueado", not is_blockchain_unlocked(cycle))

    v.check("12 evento HUMAN_APPROVAL_REQUESTED", _has_event(cycle, "HUMAN_APPROVAL_REQUESTED"))
    v.check("12b sem CALCULATION_APPROVED", not _has_event(cycle, "CALCULATION_APPROVED"))
    v.check("12c RAW_FILE_HASH_CREATED", _has_event(cycle, "RAW_FILE_HASH_CREATED"))
    v.check("12d WRAPPER_EXECUTION_STARTED", _has_event(cycle, "WRAPPER_EXECUTION_STARTED"))
    v.check("12e metadados cycle_id/layout_id", bool(cycle.get("cycle_id")) and bool(cycle.get("layout_id")))

    # Guard: cálculo sem semântica
    bad = cycle_state.new_cycle("X", "Y", "2026-01")
    bad["ontology"] = {"entities_created": 1}
    bad = orch.run_calculation_step(bad)
    v.check(
        "13 guard cálculo sem semântica",
        bad["steps"]["calculation"]["status"] == "ERROR",
    )

    return _finish(v)


def _finish(v: Validator) -> int:
    print()
    if v.errors:
        print(f"Frontend pipeline validation: FAIL ({len(v.errors)} erro(s))")
        for e in v.errors:
            print(f"  - {e}")
        return 1
    print("Frontend pipeline validation: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
