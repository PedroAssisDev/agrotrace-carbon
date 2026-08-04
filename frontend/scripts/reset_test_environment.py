#!/usr/bin/env python
"""Reset determinístico do ambiente de teste do protótipo.

Apaga apenas dados gerados (ciclos, DBs, artefatos). Nunca apaga código.
Não é executado automaticamente ao iniciar o frontend.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from services.bootstrap import wipe_all_test_data  # noqa: E402
from utils.file_helpers import invalidate_cycle_cache  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset do ambiente de teste AgroTrace Carbon")
    parser.add_argument("--confirm", action="store_true", help="Confirma a exclusão de dados gerados")
    args = parser.parse_args()
    if not args.confirm:
        print("Uso: python scripts/reset_test_environment.py --confirm")
        print("Diretórios afetados: cycles, normalized, publications, evidence_packages,")
        print("  ontology_exports, properties, originals (save-file), provenance.db, blockchain_service.db")
        return 2

    result = wipe_all_test_data(recreate_dbs=True)
    invalidate_cycle_cache()
    print("Reset concluído.")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
