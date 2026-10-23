"""Reset local e importação: simulados (FARM-*) + Embrapa (P-* / BR-*).

Fluxo:
  wipe → gerar emulados → importar emulados → importar embrapa/monthly → embrapa/annual (year=2022)

Uso:
    python scripts/reset_and_seed_pending_cycles.py --confirm
    python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42 --profile demo
    python scripts/reset_and_seed_pending_cycles.py --confirm --skip-embrapa
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
from services.embrapa_import_service import (  # noqa: E402
    ANNUAL_DEFAULT_YEAR,
    ensure_embrapa_split,
    import_embrapa_uploads,
)
from services.emulated_import_service import import_emulated_manifest  # noqa: E402
from utils.file_helpers import list_cycles  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Reset e importação: simulados (FARM-*) + Embrapa monthly/annual "
            "(propriedades distintas P-* e BR-*)."
        )
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Confirma apagamento de dados locais e execução do import.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Seed RNG dos simulados (default: 42)")
    parser.add_argument(
        "--profile",
        choices=("demo", "full"),
        default="demo",
        help="demo=17 entradas/17 ciclos (sem diário); full=perfis extras",
    )
    parser.add_argument(
        "--skip-embrapa",
        action="store_true",
        help="Importa apenas simulados (não carrega pastas Embrapa).",
    )
    parser.add_argument(
        "--embrapa-year",
        type=int,
        default=ANNUAL_DEFAULT_YEAR,
        help=f"Ano dos inventários anuais Embrapa (default: {ANNUAL_DEFAULT_YEAR})",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if not args.confirm:
        print("Operacao destrutiva: use --confirm para resetar e importar.")
        print("Exemplo: python scripts/reset_and_seed_pending_cycles.py --confirm --seed 42")
        return 1

    print("1/3 Reset + geração/importação de simulados (FARM-*)...")
    emulated = import_emulated_manifest(
        wipe_first=True,
        regenerate=True,
        global_seed=args.seed,
        profile_mode=args.profile,
    )

    errors: list[str] = []
    if args.profile == "demo":
        validate_seed_collection(list_cycles(), errors)

    embrapa = None
    if not args.skip_embrapa:
        print(
            f"2/3 Preparando split + importando Embrapa monthly (P-*) "
            f"+ annual (BR-*, year={args.embrapa_year})..."
        )
        ensure_embrapa_split()
        embrapa = import_embrapa_uploads(
            annual_year=args.embrapa_year,
            ensure_split=False,
            require_nonempty=True,
        )
    else:
        print("2/3 Embrapa ignorado (--skip-embrapa).")

    if errors:
        print("\nImport concluido com falhas de validacao (seed simulado):")
        for err in errors:
            print(f"  - {err}")
        return 1

    all_cycles = list_cycles()
    print("\n3/3 Reset concluido.\n")
    print("Bancos recriados:")
    print("- provenance.db")
    print("- blockchain_service.db")
    print(f"\nSimulados: {emulated.entry_count} entradas -> {emulated.approval_group_count} ciclos")
    if embrapa is not None:
        print(
            f"Embrapa: {embrapa.monthly_count} mensais (P-*) + "
            f"{embrapa.annual_count} anuais (BR-*) -> {len(embrapa.cycles_created)} ciclos"
        )
        print(f"Propriedades Embrapa: {len(embrapa.property_ids)}")
    print(f"Total de ciclos no disco: {len(all_cycles)}")
    print("\nAmostra (simulados):")
    for cycle in emulated.cycles_created[:3]:
        st = resolve_managerial_status(cycle)
        coverage = (cycle.get("temporal_coverage") or {}).get("label", "")
        print(f"- {cycle['cycle_id']} — {st.label} — {coverage or cycle.get('reporting_period')}")
    if embrapa and embrapa.cycles_created:
        print("\nAmostra (Embrapa):")
        for cycle in embrapa.cycles_created[:3]:
            st = resolve_managerial_status(cycle)
            coverage = (cycle.get("temporal_coverage") or {}).get("label", "")
            print(
                f"- {cycle['cycle_id']} — {st.label} — "
                f"{cycle.get('property_id')} — {coverage or cycle.get('reporting_period')}"
            )
        if len(embrapa.cycles_created) > 3:
            print(f"- ... e mais {len(embrapa.cycles_created) - 3} ciclos Embrapa")
    print("\nStatus final esperado:")
    print("- CalculationPreliminary / PendingApproval")
    print("- NotPublished / EvidenceNotGenerated / blockchain bloqueado")
    print("\nAcao esperada no front:")
    print("- acessar Revisao e Aprovacao; filtrar por fazenda P-*/BR-*/FARM-*.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
