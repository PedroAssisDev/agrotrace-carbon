# Runbook — agrotrace-carbon-provenance-service

## 0. Current phase decision

- This phase is **SQLite-first and SQLite-only**.
- Local execution, test strategy, and operational procedures below assume SQLite.
- Keep `PROV_DATABASE_URL` on SQLite URLs for this phase.

## 1. Prerequisites

- Python 3.11+ (see `pyproject.toml`)
- `pip`
- **No Docker required** for the default local flow (SQLite)

## 2. Local development (SQLite, default)

From the repository root:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate

pip install -e ".[dev]"
python scripts/init_local_db.py
# or: provenance-init-local-db

provenance-service
# or: uvicorn provenance_service.main:app --reload
# or: python -m provenance_service.main
```

- API: `http://localhost:8080`
- OpenAPI: `http://localhost:8080/docs`
- `GET /healthz`, `GET /readyz`, `GET /metrics`

The default `PROV_DATABASE_URL` is `sqlite:///./data/provenance.db`. Tables are created with SQLAlchemy `create_all` (not Alembic). Override `PROV_DATABASE_URL` for a different path or `sqlite:///:memory:`.

Optional: outbox worker in a second terminal:

```bash
provenance-outbox-worker
```

## 3. Tests

```bash
pytest -m unit
pytest
```

Integration and invariant tests use a **temporary SQLite file** (no Docker). Set `PROV_SKIP_INTEGRATION_TESTS=1` to skip them.

## 4. Environment variables

All settings use the prefix `PROV_`. See `.env.example` if present, or `src/provenance_service/infrastructure/config/settings.py`.

## 5. Operations notes

- **SQLite append-only:** `install_sqlite_append_only` runs after `create_all`
  (see `local_db_init.py` and `infrastructure/db/sqlite_append_only.py`).
  Mutable tables (`pipeline_pipeline_run`, `calculation_calculation_result_set`,
  `audit_outbox_event`, …) allow controlled updates; ledger facts are blocked
  at the database layer. `prov_core_prov_entity` allows UPDATE only for
  `invalidated_at` (soft invalidation).
- **Idempotency:** POST writes on pipeline, semantic integration, and
  calculation execution require `idempotency_key` in the JSON body.
- **Integrity:** `GET /api/v1/audit/verify/{bundle_id}` recomputes hashes where
  possible and reports `verification_mode` per subject.
- **Alembic:** not part of the default SQLite operational path for this phase.
