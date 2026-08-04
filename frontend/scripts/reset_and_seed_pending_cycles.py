"""Reset local e importação de uploads emulados pela pipeline real.

Gera CSVs em save-file/data/emulated_uploads/ e importa até pendência de aprovação.

Uso:
    python scripts/reset_and_seed_pending_cycles.py --confirm
    python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42 --profile demo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from scripts._pending_seed_assertions import validate_seed_collection  # noqa: E402
from services.cycle_status_service import resolve_managerial_status  # noqa: E402
from services.emulated_import_service import import_emulated_manifest  # noqa: E402
from utils.file_helpers import list_cycles  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset e importação de uploads emulados (pipeline até revisão humana)."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirma apagamento de dados locais e execução do import.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Seed RNG (default: 42)")
    parser.add_argument(
        "--profile",
        choices=("demo", "full"),
        default="demo",
        help="demo=198 entradas/23 ciclos; full=perfis extras",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.confirm:
        print("Operacao destrutiva: use --confirm para resetar e importar emulados.")
        print("Exemplo: python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42")
        return 1

    print("Resetando dados locais, gerando emulados e importando pela pipeline...")
    result = import_emulated_manifest(
        wipe_first=True,
        regenerate=True,
        global_seed=args.seed,
        profile_mode=args.profile,
    )

    errors: list[str] = []
    if args.profile == "demo":
        validate_seed_collection(list_cycles(), errors)

    if errors:
        print("\nImport concluido com falhas de validacao:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("\nReset concluido.\n")
    print("Bancos recriados:")
    print("- provenance.db")
    print("- blockchain_service.db")
    print(f"\nEntradas de dados: {result.entry_count}")
    print(f"Ciclos em PendingApproval: {result.approval_group_count}")
    print("\nCiclos criados (amostra):")
    for cycle in result.cycles_created[:5]:
        st = resolve_managerial_status(cycle)
        coverage = (cycle.get("temporal_coverage") or {}).get("label", "")
        print(f"- {cycle['cycle_id']} — {st.label} — {coverage or cycle.get('reporting_period')}")
    if len(result.cycles_created) > 5:
        print(f"- ... e mais {len(result.cycles_created) - 5} ciclos")
    print("\nStatus final esperado:")
    print("- CalculationPreliminary / PendingApproval")
    print("- NotPublished / EvidenceNotGenerated / blockchain bloqueado")
    print("\nAcao esperada no front:")
    print("- acessar Revisao e Aprovacao; aprovar ou reprovar manualmente.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
