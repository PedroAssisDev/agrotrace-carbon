"""Persistência SQLite de training runs e locks de concorrência."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from model_training_service.api.contracts import TrainingRunRecord
from model_training_service.domain.enums import TrainingRunStatus
from model_training_service.domain.errors import TrainingConflictError

_THREAD_LOCAL = threading.local()


class TrainingRunStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS training_runs (
                    run_id TEXT PRIMARY KEY,
                    property_id TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    current_stage TEXT NOT NULL,
                    requested_models TEXT NOT NULL,
                    configuration TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    models_created TEXT NOT NULL DEFAULT '[]',
                    models_failed TEXT NOT NULL DEFAULT '[]',
                    models_skipped TEXT NOT NULL DEFAULT '[]',
                    models_ineligible TEXT NOT NULL DEFAULT '[]',
                    error_summary TEXT
                );
                CREATE TABLE IF NOT EXISTS training_locks (
                    logical_key TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    acquired_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_runs_property
                    ON training_runs(property_id, started_at DESC);
                """
            )

    def create_run(
        self,
        *,
        property_id: str,
        mode: str,
        requested_models: list[dict[str, Any]],
        configuration: dict[str, Any],
    ) -> TrainingRunRecord:
        run_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()
        record = TrainingRunRecord(
            run_id=run_id,
            property_id=property_id,
            mode=mode,
            status=TrainingRunStatus.PENDING.value,
            current_stage="Aguardando início",
            requested_models=requested_models,
            configuration=configuration,
            started_at=now,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO training_runs (
                    run_id, property_id, mode, status, current_stage,
                    requested_models, configuration, started_at,
                    models_created, models_failed, models_skipped, models_ineligible
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '[]', '[]', '[]', '[]')
                """,
                (
                    record.run_id,
                    record.property_id,
                    record.mode,
                    record.status,
                    record.current_stage,
                    json.dumps(requested_models, ensure_ascii=False),
                    json.dumps(configuration, ensure_ascii=False),
                    record.started_at,
                ),
            )
        return record

    def update_run(self, run_id: str, **fields: Any) -> TrainingRunRecord:
        allowed = {
            "status",
            "current_stage",
            "finished_at",
            "models_created",
            "models_failed",
            "models_skipped",
            "models_ineligible",
            "error_summary",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return self.get_run(run_id)
        cols = []
        values: list[Any] = []
        for key, value in updates.items():
            cols.append(f"{key} = ?")
            if key.startswith("models_") and not isinstance(value, str):
                values.append(json.dumps(value, ensure_ascii=False))
            else:
                values.append(value)
        values.append(run_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE training_runs SET {', '.join(cols)} WHERE run_id = ?",
                values,
            )
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> TrainingRunRecord:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM training_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"Training run não encontrado: {run_id}")
        return _row_to_record(row)

    def list_runs(self, property_id: str | None = None, limit: int = 20) -> list[TrainingRunRecord]:
        with self._connect() as conn:
            if property_id:
                rows = conn.execute(
                    """
                    SELECT * FROM training_runs
                    WHERE property_id = ?
                    ORDER BY started_at DESC
                    LIMIT ?
                    """,
                    (property_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM training_runs
                    ORDER BY started_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [_row_to_record(row) for row in rows]

    def list_active_runs(self, property_id: str | None = None) -> list[TrainingRunRecord]:
        active = (
            TrainingRunStatus.PENDING.value,
            TrainingRunStatus.RUNNING.value,
        )
        with self._connect() as conn:
            if property_id:
                rows = conn.execute(
                    """
                    SELECT * FROM training_runs
                    WHERE property_id = ? AND status IN (?, ?)
                    ORDER BY started_at DESC
                    """,
                    (property_id, *active),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM training_runs
                    WHERE status IN (?, ?)
                    ORDER BY started_at DESC
                    """,
                    active,
                ).fetchall()
        return [_row_to_record(row) for row in rows]

    def acquire_locks(self, logical_keys: list[str], run_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            for key in logical_keys:
                existing = conn.execute(
                    "SELECT run_id FROM training_locks WHERE logical_key = ?",
                    (key,),
                ).fetchone()
                if existing is not None:
                    other = existing["run_id"]
                    if other != run_id:
                        raise TrainingConflictError(
                            f"Treinamento já em andamento para {key}.",
                            run_id=other,
                        )
                conn.execute(
                    """
                    INSERT INTO training_locks(logical_key, run_id, acquired_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(logical_key) DO UPDATE SET
                        run_id=excluded.run_id,
                        acquired_at=excluded.acquired_at
                    """,
                    (key, run_id, now),
                )

    def release_locks(self, run_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM training_locks WHERE run_id = ?", (run_id,))

    def find_lock_run(self, logical_key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT run_id FROM training_locks WHERE logical_key = ?",
                (logical_key,),
            ).fetchone()
        return None if row is None else str(row["run_id"])


def _row_to_record(row: sqlite3.Row) -> TrainingRunRecord:
    def _loads(raw: str | None) -> list:
        if not raw:
            return []
        try:
            payload = json.loads(raw)
        except Exception:
            return []
        return payload if isinstance(payload, list) else []

    def _loads_obj(raw: str | None) -> dict:
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    return TrainingRunRecord(
        run_id=row["run_id"],
        property_id=row["property_id"],
        mode=row["mode"],
        status=row["status"],
        current_stage=row["current_stage"],
        requested_models=_loads(row["requested_models"]),
        configuration=_loads_obj(row["configuration"]),
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        models_created=_loads(row["models_created"]),
        models_failed=_loads(row["models_failed"]),
        models_skipped=_loads(row["models_skipped"]),
        models_ineligible=_loads(row["models_ineligible"]),
        error_summary=row["error_summary"],
    )
