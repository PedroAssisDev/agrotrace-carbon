"""Importa uploads emulados pela pipeline (Fase B).

Uso:
    python scripts/import_emulated_uploads.py --confirm
    python scripts/import_emulated_uploads.py --confirm --seed 42 --profile demo
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from services.emulated_import_service import import_emulated_manifest  # noqa: E402
from services.cycle_status_service import resolve_managerial_status  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa dados emulados pela pipeline.")
    parser.add_argument("--confirm", action="store_true", help="Confirma wipe + importação.")
    parser.add_argument("--seed", type=int, default=42, help="Seed para regeneração (default: 42)")
    parser.add_argument("--profile", choices=("demo", "full"), default="demo")
    parser.add_argument(
        "--no-regenerate",
        action="store_true",
        help="Usa manifest/CSVs já existentes em emulated_uploads/",
    )
    parser.add_argument(
        "--no-wipe",
        action="store_true",
        help="Não apaga dados locais antes de importar",
    )
    args = parser.parse_args()

    if not args.confirm:
        print("Operação destrutiva: use --confirm para importar emulados.")
        print("Exemplo: python scripts/import_emulated_uploads.py --confirm --seed 42")
        return 1

    print("Importando uploads emulados pela pipeline...")
    result = import_emulated_manifest(
        wipe_first=not args.no_wipe,
        regenerate=not args.no_regenerate,
        global_seed=args.seed,
        profile_mode=args.profile,
    )
    print(f"\nManifest: {result.manifest_path}")
    print(f"Entradas: {result.entry_count}")
    print(f"Ciclos criados: {result.approval_group_count}")
    print("\nAmostra de ciclos:")
    for cycle in result.cycles_created[:5]:
        st = resolve_managerial_status(cycle)
        print(f"- {cycle['cycle_id']} — {st.label} — {cycle.get('property_name')}")
    if len(result.cycles_created) > 5:
        print(f"- ... e mais {len(result.cycles_created) - 5} ciclos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
