"""Apaga todos os dados de teste locais do protótipo (sem re-seed).

Uso:
    python scripts/wipe_test_data.py --confirm
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from services.bootstrap import wipe_all_test_data  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Apaga dados de teste locais.")
    parser.add_argument("--confirm", action="store_true", help="Confirma a remoção.")
    args = parser.parse_args()

    if not args.confirm:
        print("Operacao destrutiva: use --confirm para apagar todos os dados de teste.")
        print("Exemplo: python scripts/wipe_test_data.py --confirm")
        return 1

    print("Apagando dados de teste...")
    result = wipe_all_test_data(recreate_dbs=True)
    wiped = result.get("wiped") or {}
    print("\nLimpeza concluida.\n")
    print("Pastas esvaziadas:")
    for name, count in wiped.items():
        print(f"- {name}: {count} item(ns) removido(s)")
    print("\nBancos recriados (vazios):")
    print("- provenance.db")
    print("- blockchain_service.db")
    print("\nReinicie o frontend (python main.py) para comecar sem dados de teste.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
