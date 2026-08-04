"""Report row counts per table in the SQLite provenance database."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, text

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from demo_config import create_session_stack, ensure_local_database  # noqa: E402
from demo_tables import EXPECTED_TABLES, TABLES_BY_CONTEXT  # noqa: E402


def main() -> int:
    ensure_local_database()
    engine, _, _ = create_session_stack()
    inspector = inspect(engine)
    all_tables = sorted(inspector.get_table_names())

    counts: dict[str, int] = {}
    with engine.connect() as conn:
        for table in all_tables:
            row = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            counts[table] = int(row or 0)

    print("\n=== Table coverage report ===\n")
    filled_expected = 0
    empty_expected: list[str] = []

    for table in EXPECTED_TABLES:
        n = counts.get(table, 0)
        if n > 0:
            filled_expected += 1
            print(f"[OK] {table}: {n} registros")
        else:
            empty_expected.append(table)
            print(f"[WARN] {table}: 0 registros")

    print("\n--- Outras tabelas no banco ---")
    for table in all_tables:
        if table not in EXPECTED_TABLES:
            print(f"[INFO] {table}: {counts.get(table, 0)} registros")

    print("\n--- Por contexto ---")
    for ctx, tables in TABLES_BY_CONTEXT.items():
        ctx_filled = sum(1 for t in tables if counts.get(t, 0) > 0)
        print(f"  {ctx}: {ctx_filled}/{len(tables)} tabelas preenchidas")

    total_found = len(all_tables)
    total_filled = sum(1 for t in all_tables if counts.get(t, 0) > 0)
    total_empty = total_found - total_filled
    pct = (filled_expected / len(EXPECTED_TABLES) * 100) if EXPECTED_TABLES else 0.0

    print("\n=== Resumo ===")
    print(f"Tabelas encontradas: {total_found}")
    print(f"Tabelas esperadas preenchidas: {filled_expected}/{len(EXPECTED_TABLES)}")
    print(f"Tabelas esperadas vazias: {len(empty_expected)}")
    print(f"Tabelas com dados (todas): {total_filled}")
    print(f"Tabelas vazias (todas): {total_empty}")
    print(f"Cobertura das tabelas esperadas: {pct:.1f}%")

    engine.dispose()
    return 0 if not empty_expected else 0


if __name__ == "__main__":
    raise SystemExit(main())
