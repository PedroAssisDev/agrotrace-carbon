"""Importa CSVs Embrapa pela pipeline real (sem wipe).

Uso:
    python scripts/import_embrapa.py
    python scripts/import_embrapa.py --only daily
    python scripts/import_embrapa.py --only monthly annual
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from services.cycle_status_service import resolve_managerial_status  # noqa: E402
from services.embrapa_import_service import (  # noqa: E402
    ANNUAL_DEFAULT_YEAR,
    import_embrapa_uploads,
)

_SETS = ("monthly", "annual", "daily")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Importa pastas Embrapa (monthly/annual/daily) até pendência de aprovação."
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=_SETS,
        help="Importa apenas os conjuntos indicados (default: todos).",
    )
    parser.add_argument(
        "--embrapa-year",
        type=int,
        default=ANNUAL_DEFAULT_YEAR,
        help=f"Ano dos inventários anuais (default: {ANNUAL_DEFAULT_YEAR})",
    )
    return parser.parse_args()


def _row_count(cycle: dict) -> int:
    wrapper = cycle.get("wrapper") or {}
    if wrapper.get("rows_valid") is not None:
        return int(wrapper["rows_valid"])
    return len(cycle.get("normalized_data") or [])


def main() -> int:
    args = _parse_args()
    selected = set(args.only) if args.only else set(_SETS)
    label = ", ".join(sorted(selected))
    print(f"Importando Embrapa {label} (sem wipe)...")

    result = import_embrapa_uploads(
        annual_year=args.embrapa_year,
        include_monthly="monthly" in selected,
        include_annual="annual" in selected,
        include_daily="daily" in selected,
    )
    print(
        f"Embrapa: {result.monthly_count} mensais + {result.annual_count} anuais + "
        f"{result.daily_count} diários -> {len(result.cycles_created)} ciclos"
    )
    print(f"Propriedades: {', '.join(result.property_ids) or '—'}")
    for cycle in result.cycles_created[:5]:
        st = resolve_managerial_status(cycle)
        coverage = (cycle.get("temporal_coverage") or {}).get("label", "")
        print(
            f"- {cycle.get('cycle_id')} — {st.label} — {cycle.get('property_id')} — "
            f"{coverage or cycle.get('reporting_period')} (rows={_row_count(cycle)})"
        )
    extra = len(result.cycles_created) - 5
    if extra > 0:
        print(f"- ... e mais {extra} ciclos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
