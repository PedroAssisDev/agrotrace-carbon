"""Valida a numeração oficial de requisitos e cenários (impede IDs divergentes).

Fonte alinhada ao PDF: docs/audits/current/09-resultados.json.
Garante RF001-RF021, RNF001-RNF012, CE1-CE5 (contíguos, sem faltas/extras).

Uso:
    python frontend/scripts/validate_requirements_ids.py
    python frontend/scripts/validate_requirements_ids.py --data-root <ignorado>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPO / "docs" / "audits" / "current" / "09-resultados.json"

EXPECTED = {
    "RF": [f"RF{n:03d}" for n in range(1, 22)],   # RF001..RF021
    "RNF": [f"RNF{n:03d}" for n in range(1, 13)],  # RNF001..RNF012
    "CE": [f"CE{n}" for n in range(1, 6)],          # CE1..CE5
}


def _ids(items: list[dict]) -> list[str]:
    return [str(it.get("id")) for it in items or []]


def validate(source: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(source.read_text(encoding="utf-8"))
    for group, expected in EXPECTED.items():
        found = _ids(data.get(group) or [])
        if found != expected:
            missing = [i for i in expected if i not in found]
            extra = [i for i in found if i not in expected]
            if missing:
                errors.append(f"{group}: IDs ausentes: {missing}")
            if extra:
                errors.append(f"{group}: IDs inesperados: {extra}")
            if not missing and not extra and found != expected:
                errors.append(f"{group}: ordem divergente da oficial")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida IDs oficiais de requisitos/cenários")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--data-root", type=Path, default=None, help="Ignorado (compat regressão)")
    args = parser.parse_args()
    if not args.source.exists():
        print(f"FAIL: fonte ausente: {args.source}")
        return 1
    errors = validate(args.source)
    if errors:
        print("FAIL: numeração divergente da oficial:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS: RF001-RF021, RNF001-RNF012, CE1-CE5 conforme numeração oficial.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
