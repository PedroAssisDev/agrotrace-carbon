"""Testes unitários do validador SQL de proveniência.

Uso:
    python scripts/test_provenance_sql_validator.py
"""

from __future__ import annotations

import sys
from pathlib import Path

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
if str(FRONTEND_ROOT) not in sys.path:
    sys.path.insert(0, str(FRONTEND_ROOT))

from services.provenance_sql_validator import validate_provenance_sql  # noqa: E402


class Validator:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.ok: list[str] = []

    def check(self, name: str, condition: bool, detail: str = "") -> None:
        if condition:
            self.ok.append(name)
            print(f"  [OK]   {name}")
        else:
            msg = f"{name}{f' — {detail}' if detail else ''}"
            self.errors.append(msg)
            print(f"  [FAIL] {msg}")


def main() -> int:
    v = Validator()
    print("=== test_provenance_sql_validator ===\n")

    allowed = {"audit_outbox_event", "pipeline_pipeline_run"}

    r = validate_provenance_sql("SELECT * FROM audit_outbox_event", allowed_tables=allowed)
    v.check("SELECT simples permitido", r.ok)

    r = validate_provenance_sql(
        "WITH cte AS (SELECT 1 AS x FROM audit_outbox_event) SELECT x FROM cte",
        allowed_tables=allowed,
    )
    v.check("WITH permitido", r.ok)

    for bad_sql, label in [
        ("DELETE FROM audit_outbox_event", "DELETE"),
        ("UPDATE audit_outbox_event SET status='x'", "UPDATE"),
        ("INSERT INTO audit_outbox_event VALUES (1)", "INSERT"),
        ("DROP TABLE audit_outbox_event", "DROP"),
        ("ALTER TABLE audit_outbox_event ADD COLUMN x TEXT", "ALTER"),
    ]:
        r = validate_provenance_sql(bad_sql, allowed_tables=allowed)
        v.check(f"{label} bloqueado", not r.ok)

    r = validate_provenance_sql(
        "SELECT 1; SELECT 2 FROM audit_outbox_event",
        allowed_tables=allowed,
    )
    v.check("múltiplas instruções bloqueadas", not r.ok)

    r = validate_provenance_sql(
        "SELECT * FROM secret_users",
        allowed_tables=allowed,
    )
    v.check("tabela fora do allowlist bloqueada", not r.ok)

    r = validate_provenance_sql(
        "SELECT * FROM audit_outbox_event",
        limit=100,
        max_rows=500,
        allowed_tables=allowed,
    )
    v.check("LIMIT adicionado quando ausente", "LIMIT" in r.sql.upper())

    r = validate_provenance_sql(
        "SELECT * FROM audit_outbox_event LIMIT 9999",
        limit=100,
        max_rows=500,
        allowed_tables=allowed,
    )
    v.check("LIMIT clamped ao máximo", "LIMIT 500" in r.sql.upper() or "LIMIT 100" in r.sql.upper())

    r = validate_provenance_sql("", allowed_tables=allowed)
    v.check("consulta vazia bloqueada", not r.ok)

    print(f"\n{len(v.ok)} OK, {len(v.errors)} FAIL")
    return 1 if v.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
