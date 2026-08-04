"""Smoke tests against real PostgreSQL repositories."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from provenance_service.domain.audit.entities import OutboxEvent
from provenance_service.domain.pipeline.entities import (
    PipelineRun,
    SourceArtifact,
)
from provenance_service.domain.prov_core.entities import (
    ProvAgent,
    ProvBundle,
    ProvEntity,
)
from provenance_service.domain.shared.enums import (
    OutboxStatus,
    PipelineRunStatus,
    ProvAgentType,
    ProvBundleStatus,
    ProvBundleType,
    ProvEntityType,
)
from provenance_service.domain.shared.ids import new_uuid7


def test_pipeline_run_repository_round_trip(uow_factory) -> None:
    run_id = new_uuid7()
    with uow_factory() as uow:
        uow.pipeline_runs.add(
            PipelineRun(
                pipeline_run_id=run_id,
                run_code="repo-1",
                farm_reference="farm-1",
                reporting_period_reference="2026-Q1",
                run_status=PipelineRunStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
        )
        uow.commit()

    with uow_factory() as uow2:
        run = uow2.pipeline_runs.get(run_id)
        assert run is not None
        assert run.run_code == "repo-1"
        assert uow2.pipeline_runs.get_by_run_code("repo-1").pipeline_run_id == run_id


def test_source_artifact_idempotency_lookup(uow_factory) -> None:
    run_id = new_uuid7()
    bundle_id = new_uuid7()
    entity_id = new_uuid7()
    artifact_id = new_uuid7()
    with uow_factory() as uow:
        uow.pipeline_runs.add(
            PipelineRun(
                pipeline_run_id=run_id,
                run_code="repo-2",
                farm_reference="farm-1",
                reporting_period_reference="2026-Q1",
                run_status=PipelineRunStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
            )
        )
        uow.prov_bundles.add(
            ProvBundle(
                bundle_id=bundle_id,
                pipeline_run_id=run_id,
                bundle_type=ProvBundleType.PIPELINE_RUN,
                status=ProvBundleStatus.OPEN,
                created_at=datetime.now(timezone.utc),
            )
        )
        uow.prov_entities.add(
            ProvEntity(
                entity_id=entity_id,
                bundle_id=bundle_id,
                pipeline_run_id=run_id,
                entity_type=ProvEntityType.SOURCE_ARTIFACT,
                created_at=datetime.now(timezone.utc),
            )
        )
        uow.flush()
        uow.source_artifacts.add(
            SourceArtifact(
                source_artifact_id=artifact_id,
                pipeline_run_id=run_id,
                prov_entity_id=entity_id,
                source_system="ERP",
                original_filename="x.xml",
                storage_uri="s3://x.xml",
                content_hash="aa" * 32,
                received_at=datetime.now(timezone.utc),
                idempotency_key="src-key-1",
            )
        )
        uow.commit()

    with uow_factory() as uow2:
        same = uow2.source_artifacts.get_by_idempotency_key("src-key-1")
        assert same is not None
        assert same.source_artifact_id == artifact_id


def test_prov_agent_lookup_by_external_reference(uow_factory) -> None:
    agent_id = new_uuid7()
    with uow_factory() as uow:
        uow.prov_agents.add(
            ProvAgent(
                agent_id=agent_id,
                agent_type=ProvAgentType.SOFTWARE,
                name="erp-wrapper",
                external_reference="wrapper:erp@1.0.0",
                created_at=datetime.now(timezone.utc),
            )
        )
        uow.commit()

    with uow_factory() as uow2:
        agent = uow2.prov_agents.get_by_external_reference("wrapper:erp@1.0.0")
        assert agent is not None
        assert agent.agent_id == agent_id


def test_outbox_pending_listing_and_mark_published(uow_factory) -> None:
    event_id = new_uuid7()
    with uow_factory() as uow:
        uow.outbox.add(
            OutboxEvent(
                outbox_event_id=event_id,
                aggregate_kind="pipeline_run",
                aggregate_id=uuid4(),
                event_type="test.event",
                payload={"hello": "world"},
                created_at=datetime.now(timezone.utc),
                status=OutboxStatus.PENDING,
            )
        )
        uow.commit()

    with uow_factory() as uow2:
        pending = uow2.outbox.list_pending(10)
        assert any(e.outbox_event_id == event_id for e in pending)
        uow2.outbox.mark_published(event_id)
        uow2.commit()

    with uow_factory() as uow3:
        pending = uow3.outbox.list_pending(10)
        assert all(e.outbox_event_id != event_id for e in pending)
