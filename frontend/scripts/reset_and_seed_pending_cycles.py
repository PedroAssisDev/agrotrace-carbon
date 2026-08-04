"""Reset local e seed de ciclos pendentes de aprovação humana.

Gera 198 entradas de dados (12 mensais + 5 anuais + 181 diários) e
23 ciclos em PendingApproval (agrupamento mensal no cenário diário).

Uso:
    python scripts/reset_and_seed_pending_cycles.py --confirm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from scripts._pending_seed_assertions import validate_seed_collection  # noqa: E402
from services import local_orchestrator as orch  # noqa: E402
from services.bootstrap import reset_local_data  # noqa: E402
from services.cycle_status_service import resolve_managerial_status  # noqa: E402
from services.seed_data_builder import build_all_seed_files  # noqa: E402
from services.seed_period_planner import (
    SeedApprovalGroup,
    all_approval_groups,
    expected_approval_count,
    expected_entry_count,
)  # noqa: E402
from utils.file_helpers import list_cycles, save_cycle  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reset e seed de ciclos pendentes de aprovação.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirma apagamento de dados locais e execução do seed.",
    )
    return parser.parse_args()


def _entry_payloads(group: SeedApprovalGroup, manifest_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for entry in group.entries:
        meta = manifest_by_id[entry.entry_id]
        payloads.append({
            "entry_id": entry.entry_id,
            "path": meta["path"],
            "reporting_period": entry.reporting_period,
            "property_id": entry.property_id,
            "original_filename": Path(meta["path"]).name,
        })
    return payloads


def _seed_approval_group(
    group: SeedApprovalGroup,
    manifest_by_id: dict[str, dict[str, Any]],
    *,
    index: int,
    total: int,
) -> dict:
    entry_count = len(group.entries)
    print(
        f"  [{index}/{total}] {group.cycle_id} "
        f"({entry_count} entrada{'s' if entry_count != 1 else ''})"
    )
    cycle = orch.run_pipeline_group_until_pending(
        _entry_payloads(group, manifest_by_id),
        cycle_id=group.cycle_id,
        property_id=group.property_id,
        property_name=group.property_name,
        reporting_period=group.reporting_period,
        layout_name=group.layout,
        data_granularity=group.data_granularity,
        approval_granularity=group.approval_granularity,
        scenario_key=group.scenario_key,
        coverage_label=group.coverage_label,
    )
    save_cycle(cycle)
    return cycle


def main() -> int:
    args = _parse_args()
    if not args.confirm:
        print("Operacao destrutiva: use --confirm para resetar e semear os ciclos pendentes.")
        print("Exemplo: python scripts/reset_and_seed_pending_cycles.py --confirm")
        return 1

    print("Resetando dados locais e recriando bancos...")
    reset_local_data()

    print(f"\nGerando CSVs de seed ({expected_entry_count()} entradas)...")
    seed_result = build_all_seed_files()
    manifest_by_id = {e["entry_id"]: e for e in seed_result["manifest"]["entries"]}
    groups = all_approval_groups(seed_result["plans"])
    total_groups = expected_approval_count()

    print(f"\nSemeando {total_groups} ciclos (pipeline ate revisao humana)...")
    created: list[dict] = []
    for idx, group in enumerate(groups, start=1):
        created.append(_seed_approval_group(group, manifest_by_id, index=idx, total=total_groups))

    errors: list[str] = []
    validate_seed_collection(list_cycles(), errors, manifest=seed_result["manifest"])
    if errors:
        print("\nSeed concluido com falhas de validacao:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("\nReset concluido.\n")
    print("Bancos recriados:")
    print("- provenance.db")
    print("- blockchain_service.db")
    print(f"\nEntradas de dados: {expected_entry_count()}")
    print(f"Ciclos em PendingApproval: {total_groups}")
    print("\nCiclos criados (amostra):")
    for cycle in created[:5]:
        st = resolve_managerial_status(cycle)
        coverage = (cycle.get("temporal_coverage") or {}).get("label", "")
        print(f"- {cycle['cycle_id']} — {st.label} — {coverage}")
    if len(created) > 5:
        print(f"- ... e mais {len(created) - 5} ciclos")
    print("\nStatus final:")
    print("- CalculationPreliminary")
    print("- PendingApproval")
    print("- NotPublished")
    print("- EvidenceNotGenerated")
    print("- IntegrityNotVerified")
    print("\nAcao esperada no front:")
    print("- acessar Revisao e Aprovacao;")
    print("- revisar os calculos pendentes;")
    print("- aprovar ou reprovar manualmente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
