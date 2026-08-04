"""Gera arquivos CSV emulados e manifest.json.

Uso:
    python scripts/generate_emulated_uploads.py --seed 42
    python scripts/generate_emulated_uploads.py --seed 42 --profile full
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from save_file.emulated import (  # noqa: E402
    generate_emulated_uploads,
    validate_emulated_directory,
)
from save_file.emulated.manifest import default_emulated_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Gera uploads emulados para a pipeline.")
    parser.add_argument("--seed", type=int, default=42, help="Seed RNG global (default: 42)")
    parser.add_argument(
        "--profile",
        choices=("demo", "full"),
        default="demo",
        help="demo=3 fazendas/23 ciclos; full=perfis extras",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Pasta de saída (default: data/emulated_uploads/)",
    )
    parser.add_argument(
        "--no-wipe",
        action="store_true",
        help="Não limpar pasta antes de gerar",
    )
    args = parser.parse_args()

    out = args.output_dir or default_emulated_dir()
    result = generate_emulated_uploads(
        global_seed=args.seed,
        profile_mode=args.profile,
        output_dir=out,
        wipe=not args.no_wipe,
    )
    manifest = result["manifest"]
    errors = validate_emulated_directory(out)
    print(f"Gerados {manifest.entry_count} arquivos em {out}")
    print(f"Grupos de aprovação: {manifest.approval_group_count}")
    print(f"Manifest: {result['manifest_path']}")
    if errors:
        print("\nValidação com falhas:")
        for err in errors[:20]:
            print(f"  - {err}")
        if len(errors) > 20:
            print(f"  ... e mais {len(errors) - 20}")
        return 1
    print("Validação: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
