"""HTTP-level integration tests using FastAPI's TestClient."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(engine, db_session_factory) -> Iterator[TestClient]:  # noqa: ARG001
    os.environ["PROV_ENABLE_OUTBOX_WORKER"] = "false"
    from provenance_service.infrastructure.db import session as session_mod

    orig_get_engine = session_mod.get_engine
    orig_get_sessionmaker = session_mod.get_sessionmaker
    session_mod.get_engine.cache_clear()  # type: ignore[attr-defined]
    session_mod.get_sessionmaker.cache_clear()  # type: ignore[attr-defined]
    session_mod.get_engine = lambda: engine  # type: ignore[assignment]
    session_mod.get_sessionmaker = lambda: db_session_factory  # type: ignore[assignment]

    from provenance_service.main import _create_app

    app = _create_app()
    try:
        with TestClient(app) as c:
            yield c
    finally:
        session_mod.get_engine = orig_get_engine  # type: ignore[assignment]
        session_mod.get_sessionmaker = orig_get_sessionmaker  # type: ignore[assignment]


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readyz(client: TestClient) -> None:
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"


def test_full_pipeline_endpoints(client: TestClient) -> None:
    # 1. start a run
    r = client.post(
        "/api/v1/pipeline-runs",
        json={
            "run_code": "api-run-1",
            "farm_reference": "farm-api",
            "reporting_period_reference": "2026-Q1",
            "idempotency_key": "api-run-1-key",
        },
    )
    assert r.status_code == 201, r.text
    run = r.json()
    run_id = run["pipeline_run_id"]

    # GET round-trip
    r = client.get(f"/api/v1/pipeline-runs/{run_id}")
    assert r.status_code == 200
    assert r.json()["run_code"] == "api-run-1"

    # 2. register source artifact
    r = client.post(
        "/api/v1/source-artifacts",
        json={
            "pipeline_run_id": run_id,
            "source_system": "ERP",
            "original_filename": "data.xml",
            "storage_uri": "s3://data.xml",
            "content_hash": "a" * 64,
            "idempotency_key": "api-art-1-key",
        },
    )
    assert r.status_code == 201, r.text
    artifact = r.json()

    # 3. wrapper definition + execution
    r = client.post(
        "/api/v1/wrapper-definitions",
        json={
            "wrapper_name": "erp-xml",
            "wrapper_version": "1.0.0",
            "source_layout_name": "erp",
        },
    )
    assert r.status_code == 201
    wrapper_def = r.json()

    r = client.post(
        "/api/v1/wrapper-executions",
        json={
            "pipeline_run_id": run_id,
            "wrapper_definition_id": wrapper_def["wrapper_definition_id"],
            "input_artifact_id": artifact["source_artifact_id"],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": "api-wexec-1-key",
        },
    )
    assert r.status_code == 201, r.text
    execution = r.json()

    # 4. normalized batch
    r = client.post(
        "/api/v1/normalized-batches",
        json={
            "pipeline_run_id": run_id,
            "wrapper_execution_id": execution["wrapper_execution_id"],
            "batch_code": "batch-api-1",
            "schema_version": "1.0",
            "record_count": 1,
            "content_hash": "b" * 64,
            "idempotency_key": "api-batch-1-key",
        },
    )
    assert r.status_code == 201, r.text


def test_invariant_returns_422(client: TestClient) -> None:
    r = client.post(
        "/api/v1/pipeline-runs",
        json={
            "run_code": "v-1",
            "farm_reference": "farm",
            "reporting_period_reference": "2026-Q1",
            "idempotency_key": "v-1-run-key",
        },
    )
    assert r.status_code == 201
    run_id = r.json()["pipeline_run_id"]

    # wrapper_execution requires an existing source_artifact
    r = client.post(
        "/api/v1/wrapper-definitions",
        json={
            "wrapper_name": "e",
            "wrapper_version": "1",
            "source_layout_name": "e",
        },
    )
    wrapper_def_id = r.json()["wrapper_definition_id"]

    r = client.post(
        "/api/v1/wrapper-executions",
        json={
            "pipeline_run_id": run_id,
            "wrapper_definition_id": wrapper_def_id,
            "input_artifact_id": "00000000-0000-0000-0000-000000000000",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "idempotency_key": "v-1-wexec-key",
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert body["title"] == "Invariant Violation"


def test_problem_details_correlation_id(client: TestClient) -> None:
    r = client.get(
        "/api/v1/pipeline-runs/00000000-0000-0000-0000-000000000000",
        headers={"X-Correlation-ID": "trace-123"},
    )
    assert r.status_code == 404
    body = r.json()
    assert body["correlation_id"] == "trace-123"
    assert r.headers["X-Correlation-ID"] == "trace-123"


def test_list_pipeline_runs_with_pagination(client: TestClient) -> None:
    for idx in range(3):
        r = client.post(
            "/api/v1/pipeline-runs",
            json={
                "run_code": f"list-run-{idx}",
                "farm_reference": "farm-list",
                "reporting_period_reference": "2026-Q1",
                "idempotency_key": f"list-run-{idx}-key",
            },
        )
        assert r.status_code == 201

    r = client.get("/api/v1/pipeline-runs?limit=2&offset=0&farm_reference=farm-list")
    assert r.status_code == 200
    payload = r.json()
    assert payload["limit"] == 2
    assert payload["offset"] == 0
    assert payload["total"] >= 3
    assert len(payload["items"]) == 2


def test_list_outbox_events(client: TestClient) -> None:
    r = client.post(
        "/api/v1/pipeline-runs",
        json={
            "run_code": "outbox-run-1",
            "farm_reference": "farm-outbox",
            "reporting_period_reference": "2026-Q1",
            "idempotency_key": "outbox-run-1-key",
        },
    )
    assert r.status_code == 201

    r = client.get("/api/v1/audit/outbox-events?limit=10&offset=0")
    assert r.status_code == 200
    payload = r.json()
    assert payload["total"] >= 1
    assert payload["items"]


def test_outbox_event_type_filter(client: TestClient) -> None:
    r = client.post(
        "/api/v1/pipeline-runs",
        json={
            "run_code": "outbox-filter-run",
            "farm_reference": "farm-filter",
            "reporting_period_reference": "2026-Q1",
            "idempotency_key": "outbox-filter-run-key",
        },
    )
    assert r.status_code == 201

    r = client.get(
        "/api/v1/audit/outbox-events?event_type=pipeline_run.started&limit=50"
    )
    assert r.status_code == 200
    payload = r.json()
    assert payload["total"] >= 1
    assert all(e["event_type"] == "pipeline_run.started" for e in payload["items"])


def test_reporting_period_post_and_get(client: TestClient) -> None:
    r = client.post(
        "/api/v1/reporting-periods",
        json={
            "period_start": "2026-01-01T00:00:00+00:00",
            "period_end": "2026-02-01T00:00:00+00:00",
            "period_granularity": "monthly",
            "year": 2026,
            "month": 1,
            "period_label": "api-monthly-2026-01",
        },
    )
    assert r.status_code == 201, r.text
    period = r.json()
    period_id = period["reporting_period_id"]
    assert period["period_granularity"] == "monthly"

    r = client.get(f"/api/v1/reporting-periods/{period_id}")
    assert r.status_code == 200
    assert r.json()["period_label"] == "api-monthly-2026-01"


def test_pipeline_run_with_reporting_period_id(client: TestClient) -> None:
    r = client.post(
        "/api/v1/reporting-periods",
        json={
            "period_start": "2026-01-01T00:00:00+00:00",
            "period_end": "2026-02-01T00:00:00+00:00",
            "period_granularity": "monthly",
            "year": 2026,
            "month": 1,
            "period_label": "api-run-period-link",
        },
    )
    assert r.status_code == 201
    period_id = r.json()["reporting_period_id"]

    r = client.post(
        "/api/v1/pipeline-runs",
        json={
            "run_code": "api-run-with-period",
            "farm_reference": "farm-period",
            "reporting_period_reference": "2026-01",
            "idempotency_key": "api-run-with-period-key",
            "run_type": "monthly_calculation",
            "reporting_period_id": period_id,
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["reporting_period_id"] == period_id
    assert body["run_type"] == "monthly_calculation"


def test_bundle_graph_includes_derived_from_and_revisions(client: TestClient) -> None:
    r = client.post(
        "/api/v1/pipeline-runs",
        json={
            "run_code": "graph-run-1",
            "farm_reference": "farm-graph",
            "reporting_period_reference": "2026-Q1",
            "idempotency_key": "graph-run-1-key",
        },
    )
    assert r.status_code == 201
    run_id = r.json()["pipeline_run_id"]

    r = client.post(
        "/api/v1/source-artifacts",
        json={
            "pipeline_run_id": run_id,
            "source_system": "ERP",
            "original_filename": "data.xml",
            "storage_uri": "s3://data.xml",
            "content_hash": "a" * 64,
            "idempotency_key": "graph-art-key",
        },
    )
    assert r.status_code == 201

    r = client.get(f"/api/v1/pipeline-runs/{run_id}/trace")
    assert r.status_code == 200
    bundles = r.json()["prov_bundles"]
    assert bundles
    bundle_id = bundles[0]["bundle_id"]

    for path in (
        f"/api/v1/bundles/{bundle_id}/graph",
        f"/api/v1/pipeline-runs/{run_id}/graph",
    ):
        r = client.get(path)
        assert r.status_code == 200
        if "bundle_graphs" in r.json():
            graph = r.json()["bundle_graphs"][0]["graph"]
        else:
            graph = r.json()
        assert "derived_from" in graph
        assert "revisions" in graph
        assert isinstance(graph["derived_from"], list)
        assert isinstance(graph["revisions"], list)
