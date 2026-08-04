from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.domain.ports.provenance_ports import (
    AggregationLinkData,
    CalculationResultSetData,
    HashRecordData,
    PipelineRunData,
    ProvenanceDataReaderPort,
    ProvenanceEvent,
    ProvenanceEventReaderPort,
    ReportingPeriodData,
)
from app.shared.config import Settings, get_settings
from app.shared.exceptions import ProvenanceReadError


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _resolve_provenance_path(settings: Settings) -> Path:
    raw = settings.provenance_database_url
    if raw.startswith("sqlite:///"):
        return Path(raw.replace("sqlite:///", ""))
    path = Path(raw)
    if path.exists():
        return path
    raise ProvenanceReadError(f"Provenance database not found at: {raw}")


class SQLiteProvenanceEventReader(ProvenanceEventReaderPort):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db_path = _resolve_provenance_path(self._settings)

    def _connect(self) -> sqlite3.Connection:
        if not self._db_path.exists():
            raise ProvenanceReadError(f"Provenance database not found: {self._db_path}")
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def fetch_pending_events(
        self,
        *,
        event_types: set[str],
        after_created_at: datetime | None = None,
        limit: int = 100,
    ) -> list[ProvenanceEvent]:
        if not event_types:
            return []
        placeholders = ",".join("?" for _ in event_types)
        query = f"""
            SELECT
                outbox_event_id,
                event_type,
                status,
                created_at,
                payload,
                pipeline_run_id,
                calculation_execution_id,
                calculation_result_set_id,
                reporting_period_id,
                source_table,
                source_record_id
            FROM audit_outbox_event
            WHERE status = 'pending'
              AND event_type IN ({placeholders})
        """
        params: list[object] = list(sorted(event_types))
        if after_created_at is not None:
            query += " AND created_at > ?"
            params.append(after_created_at.isoformat())
        query += " ORDER BY created_at ASC, outbox_event_id ASC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        events: list[ProvenanceEvent] = []
        for row in rows:
            payload = json.loads(row["payload"]) if row["payload"] else {}
            events.append(
                ProvenanceEvent(
                    outbox_event_id=str(row["outbox_event_id"]),
                    event_type=row["event_type"],
                    status=row["status"],
                    created_at=_parse_dt(row["created_at"]) or datetime.now(UTC),
                    payload=payload,
                    pipeline_run_id=(
                        UUID(row["pipeline_run_id"]) if row["pipeline_run_id"] else None
                    ),
                    calculation_execution_id=(
                        UUID(row["calculation_execution_id"])
                        if row["calculation_execution_id"]
                        else None
                    ),
                    calculation_result_set_id=(
                        UUID(row["calculation_result_set_id"])
                        if row["calculation_result_set_id"]
                        else None
                    ),
                    reporting_period_id=(
                        UUID(row["reporting_period_id"]) if row["reporting_period_id"] else None
                    ),
                    source_table=row["source_table"],
                    source_record_id=(
                        UUID(row["source_record_id"]) if row["source_record_id"] else None
                    ),
                )
            )
        return events

    def get_event_by_id(self, outbox_event_id: str) -> ProvenanceEvent | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    outbox_event_id,
                    event_type,
                    status,
                    created_at,
                    payload,
                    pipeline_run_id,
                    calculation_execution_id,
                    calculation_result_set_id,
                    reporting_period_id,
                    source_table,
                    source_record_id
                FROM audit_outbox_event
                WHERE outbox_event_id = ?
                """,
                (outbox_event_id,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload"]) if row["payload"] else {}
        return ProvenanceEvent(
            outbox_event_id=str(row["outbox_event_id"]),
            event_type=row["event_type"],
            status=row["status"],
            created_at=_parse_dt(row["created_at"]) or datetime.now(UTC),
            payload=payload,
            pipeline_run_id=UUID(row["pipeline_run_id"]) if row["pipeline_run_id"] else None,
            calculation_execution_id=(
                UUID(row["calculation_execution_id"]) if row["calculation_execution_id"] else None
            ),
            calculation_result_set_id=(
                UUID(row["calculation_result_set_id"])
                if row["calculation_result_set_id"]
                else None
            ),
            reporting_period_id=(
                UUID(row["reporting_period_id"]) if row["reporting_period_id"] else None
            ),
            source_table=row["source_table"],
            source_record_id=UUID(row["source_record_id"]) if row["source_record_id"] else None,
        )


class SQLiteProvenanceDataReader(ProvenanceDataReaderPort):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._db_path = _resolve_provenance_path(self._settings)

    def _connect(self) -> sqlite3.Connection:
        if not self._db_path.exists():
            raise ProvenanceReadError(f"Provenance database not found: {self._db_path}")
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def get_reporting_period(self, reporting_period_id: UUID) -> ReportingPeriodData | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT reporting_period_id, period_start, period_end, period_granularity, period_label
                FROM reporting_period
                WHERE reporting_period_id = ?
                """,
                (str(reporting_period_id),),
            ).fetchone()
        if row is None:
            return None
        return ReportingPeriodData(
            reporting_period_id=UUID(row["reporting_period_id"]),
            period_start=_parse_dt(row["period_start"]) or datetime.now(UTC),
            period_end=_parse_dt(row["period_end"]) or datetime.now(UTC),
            period_granularity=row["period_granularity"],
            period_label=row["period_label"],
        )

    def get_pipeline_run(self, pipeline_run_id: UUID) -> PipelineRunData | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT pipeline_run_id, farm_id_hash, project_id_hash, reporting_period_id
                FROM pipeline_pipeline_run
                WHERE pipeline_run_id = ?
                """,
                (str(pipeline_run_id),),
            ).fetchone()
        if row is None:
            return None
        return PipelineRunData(
            pipeline_run_id=UUID(row["pipeline_run_id"]),
            farm_id_hash=row["farm_id_hash"],
            project_id_hash=row["project_id_hash"],
            reporting_period_id=(
                UUID(row["reporting_period_id"]) if row["reporting_period_id"] else None
            ),
        )

    def get_calculation_result_set(
        self, calculation_result_set_id: UUID
    ) -> CalculationResultSetData | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    calculation_result_set_id,
                    pipeline_run_id,
                    calculation_execution_id,
                    summary_hash,
                    result_scope,
                    consolidation_type,
                    reporting_period_id,
                    approved_at,
                    published_at
                FROM calculation_calculation_result_set
                WHERE calculation_result_set_id = ?
                """,
                (str(calculation_result_set_id),),
            ).fetchone()
        if row is None:
            return None
        return CalculationResultSetData(
            calculation_result_set_id=UUID(row["calculation_result_set_id"]),
            pipeline_run_id=UUID(row["pipeline_run_id"]),
            calculation_execution_id=UUID(row["calculation_execution_id"]),
            summary_hash=row["summary_hash"],
            result_scope=row["result_scope"],
            consolidation_type=row["consolidation_type"],
            reporting_period_id=(
                UUID(row["reporting_period_id"]) if row["reporting_period_id"] else None
            ),
            approved_at=_parse_dt(row["approved_at"]),
            published_at=_parse_dt(row["published_at"]),
        )

    def get_hash_records_for_subject(
        self, subject_kind: str, subject_id: UUID
    ) -> list[HashRecordData]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT hash_record_id, subject_kind, subject_id, hash_value, hash_scope,
                       canonicalization_method
                FROM audit_hash_record
                WHERE subject_kind = ? AND subject_id = ?
                ORDER BY computed_at ASC
                """,
                (subject_kind, str(subject_id)),
            ).fetchall()
        return [
            HashRecordData(
                hash_record_id=UUID(row["hash_record_id"]),
                subject_kind=row["subject_kind"],
                subject_id=UUID(row["subject_id"]),
                hash_value=row["hash_value"],
                hash_scope=row["hash_scope"],
                canonicalization_method=row["canonicalization_method"],
            )
            for row in rows
        ]

    def get_aggregation_link_by_id(self, link_id: UUID) -> AggregationLinkData | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT aggregation_link_id, parent_result_set_id, child_result_set_id, aggregation_type
                FROM calculation_result_aggregation_link
                WHERE aggregation_link_id = ?
                """,
                (str(link_id),),
            ).fetchone()
        if row is None:
            return None
        return AggregationLinkData(
            aggregation_link_id=UUID(row["aggregation_link_id"]),
            parent_result_set_id=UUID(row["parent_result_set_id"]),
            child_result_set_id=UUID(row["child_result_set_id"]),
            aggregation_type=row["aggregation_type"],
        )

    def get_calculation_execution_method_version_hash(
        self, calculation_execution_id: UUID
    ) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT hr.hash_value
                FROM calculation_calculation_execution ce
                JOIN calculation_calculation_method_version mv
                  ON mv.calculation_method_version_id = ce.calculation_method_version_id
                LEFT JOIN audit_hash_record hr
                  ON hr.subject_kind = 'calculation_method_version'
                 AND hr.subject_id = mv.calculation_method_version_id
                WHERE ce.calculation_execution_id = ?
                ORDER BY hr.computed_at DESC
                LIMIT 1
                """,
                (str(calculation_execution_id),),
            ).fetchone()
        return row["hash_value"] if row and row["hash_value"] else None

    def get_calculation_execution_parameter_set_hash(
        self, calculation_execution_id: UUID
    ) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT hr.hash_value
                FROM calculation_calculation_execution ce
                JOIN calculation_calculation_parameter_set ps
                  ON ps.calculation_parameter_set_id = ce.calculation_parameter_set_id
                LEFT JOIN audit_hash_record hr
                  ON hr.subject_kind = 'calculation_parameter_set'
                 AND hr.subject_id = ps.calculation_parameter_set_id
                WHERE ce.calculation_execution_id = ?
                ORDER BY hr.computed_at DESC
                LIMIT 1
                """,
                (str(calculation_execution_id),),
            ).fetchone()
        return row["hash_value"] if row and row["hash_value"] else None
