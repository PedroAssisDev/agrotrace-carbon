"""Idempotent SQLite migration: add idempotency_key to blockchain_transaction."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from app.shared.config import get_settings


def _sqlite_path_from_url(database_url: str) -> Path:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError(f"Only sqlite URLs are supported for migration: {database_url}")
    return Path(database_url.removeprefix(prefix))


def migrate(database_url: str | None = None) -> dict:
    settings = get_settings()
    url = database_url or settings.database_url
    db_path = _sqlite_path_from_url(url)
    if not db_path.exists():
        return {"status": "skipped", "reason": f"database does not exist: {db_path}"}

    conn = sqlite3.connect(db_path)
    try:
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(blockchain_transaction)").fetchall()
        }
        actions: list[str] = []
        if "idempotency_key" not in cols:
            conn.execute(
                "ALTER TABLE blockchain_transaction ADD COLUMN idempotency_key TEXT"
            )
            actions.append("added_column_idempotency_key")
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_blockchain_transaction_idempotency
            ON blockchain_transaction(idempotency_key)
            WHERE idempotency_key IS NOT NULL
            """
        )
        actions.append("ensured_unique_index")
        conn.commit()
        return {"status": "ok", "actions": actions, "database": str(db_path)}
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Add idempotency_key column safely")
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()
    result = migrate(args.database_url)
    print(result)
    return 0 if result.get("status") in {"ok", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
