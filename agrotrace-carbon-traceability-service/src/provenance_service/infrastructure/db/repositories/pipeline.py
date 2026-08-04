"""SQLAlchemy implementations of the pipeline-context repositories."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from provenance_service.domain.pipeline.entities import (
    NormalizedBatch,
    PipelineRun,
    SourceArtifact,
    SourceArtifactRevision,
    WrapperDefinition,
    WrapperExecution,
)
from provenance_service.infrastructure.db.models.pipeline import (
    NormalizedBatchModel,
    PipelineRunModel,
    SourceArtifactModel,
    SourceArtifactRevisionModel,
    WrapperDefinitionModel,
    WrapperExecutionModel,
)
from provenance_service.infrastructure.db.repositories import _mappers as M
from provenance_service.infrastructure.db.repositories._session_pending import (
    get_model_or_pending,
)


class SqlAlchemyPipelineRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, pipeline_run: PipelineRun) -> None:
        self._session.add(M.to_pipeline_run_model(pipeline_run))

    def get(self, pipeline_run_id: UUID) -> PipelineRun | None:
        m = get_model_or_pending(
            self._session, PipelineRunModel, "pipeline_run_id", pipeline_run_id
        )
        return M.from_pipeline_run_model(m) if m else None

    def get_by_run_code(self, run_code: str) -> PipelineRun | None:
        m = self._session.scalar(
            select(PipelineRunModel).where(PipelineRunModel.run_code == run_code)
        )
        return M.from_pipeline_run_model(m) if m else None

    def get_by_idempotency_key(self, key: str) -> PipelineRun | None:
        m = self._session.scalar(
            select(PipelineRunModel).where(PipelineRunModel.idempotency_key == key)
        )
        return M.from_pipeline_run_model(m) if m else None

    def list_filtered(
        self,
        *,
        limit: int,
        offset: int,
        run_status: str | None = None,
        farm_reference: str | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
    ) -> tuple[list[PipelineRun], int]:
        filters = []
        if run_status:
            filters.append(PipelineRunModel.run_status == run_status)
        if farm_reference:
            filters.append(PipelineRunModel.farm_reference == farm_reference)
        if started_from:
            filters.append(PipelineRunModel.started_at >= started_from)
        if started_to:
            filters.append(PipelineRunModel.started_at <= started_to)

        total_stmt = select(func.count()).select_from(PipelineRunModel)
        if filters:
            total_stmt = total_stmt.where(*filters)
        total = int(self._session.scalar(total_stmt) or 0)

        stmt = (
            select(PipelineRunModel)
            .order_by(PipelineRunModel.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if filters:
            stmt = stmt.where(*filters)
        rows = self._session.scalars(stmt).all()
        return [M.from_pipeline_run_model(r) for r in rows], total

    def update_status(
        self,
        pipeline_run_id: UUID,
        *,
        status: str,
        finished_at: datetime | None = None,
    ) -> None:
        stmt = (
            update(PipelineRunModel)
            .where(PipelineRunModel.pipeline_run_id == pipeline_run_id)
            .values(run_status=status, finished_at=finished_at)
        )
        self._session.execute(stmt)


class SqlAlchemySourceArtifactRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, source_artifact: SourceArtifact) -> None:
        self._session.add(M.to_source_artifact_model(source_artifact))

    def get(self, source_artifact_id: UUID) -> SourceArtifact | None:
        m = get_model_or_pending(
            self._session, SourceArtifactModel, "source_artifact_id", source_artifact_id
        )
        return M.from_source_artifact_model(m) if m else None

    def get_by_idempotency_key(self, key: str) -> SourceArtifact | None:
        m = self._session.scalar(
            select(SourceArtifactModel).where(SourceArtifactModel.idempotency_key == key)
        )
        return M.from_source_artifact_model(m) if m else None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[SourceArtifact]:
        rows = self._session.scalars(
            select(SourceArtifactModel).where(
                SourceArtifactModel.pipeline_run_id == pipeline_run_id
            )
        ).all()
        return [M.from_source_artifact_model(m) for m in rows]


class SqlAlchemySourceArtifactRevisionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, revision: SourceArtifactRevision) -> None:
        self._session.add(M.to_source_artifact_revision_model(revision))

    def get(self, revision_id: UUID) -> SourceArtifactRevision | None:
        m = get_model_or_pending(
            self._session,
            SourceArtifactRevisionModel,
            "source_artifact_revision_id",
            revision_id,
        )
        return M.from_source_artifact_revision_model(m) if m else None

    def get_by_artifact_and_revision(
        self, source_artifact_id: UUID, revision_number: int
    ) -> SourceArtifactRevision | None:
        m = self._session.scalar(
            select(SourceArtifactRevisionModel).where(
                SourceArtifactRevisionModel.source_artifact_id == source_artifact_id,
                SourceArtifactRevisionModel.revision_number == revision_number,
            )
        )
        return M.from_source_artifact_revision_model(m) if m else None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[SourceArtifactRevision]:
        rows = self._session.scalars(
            select(SourceArtifactRevisionModel)
            .join(SourceArtifactModel)
            .where(SourceArtifactModel.pipeline_run_id == pipeline_run_id)
        ).all()
        return [M.from_source_artifact_revision_model(m) for m in rows]


class SqlAlchemyWrapperDefinitionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, wrapper_definition: WrapperDefinition) -> None:
        self._session.add(M.to_wrapper_definition_model(wrapper_definition))

    def get(self, wrapper_definition_id: UUID) -> WrapperDefinition | None:
        m = get_model_or_pending(
            self._session,
            WrapperDefinitionModel,
            "wrapper_definition_id",
            wrapper_definition_id,
        )
        return M.from_wrapper_definition_model(m) if m else None

    def get_by_name_version(self, name: str, version: str) -> WrapperDefinition | None:
        m = self._session.scalar(
            select(WrapperDefinitionModel).where(
                WrapperDefinitionModel.wrapper_name == name,
                WrapperDefinitionModel.wrapper_version == version,
            )
        )
        return M.from_wrapper_definition_model(m) if m else None

    def deactivate(self, wrapper_definition_id: UUID) -> None:
        stmt = (
            update(WrapperDefinitionModel)
            .where(WrapperDefinitionModel.wrapper_definition_id == wrapper_definition_id)
            .values(is_active=False)
        )
        self._session.execute(stmt)


class SqlAlchemyWrapperExecutionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, wrapper_execution: WrapperExecution) -> None:
        self._session.add(M.to_wrapper_execution_model(wrapper_execution))

    def get(self, wrapper_execution_id: UUID) -> WrapperExecution | None:
        m = get_model_or_pending(
            self._session, WrapperExecutionModel, "wrapper_execution_id", wrapper_execution_id
        )
        return M.from_wrapper_execution_model(m) if m else None

    def get_by_idempotency_key(self, key: str) -> WrapperExecution | None:
        m = self._session.scalar(
            select(WrapperExecutionModel).where(
                WrapperExecutionModel.idempotency_key == key
            )
        )
        return M.from_wrapper_execution_model(m) if m else None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[WrapperExecution]:
        rows = self._session.scalars(
            select(WrapperExecutionModel).where(
                WrapperExecutionModel.pipeline_run_id == pipeline_run_id
            )
        ).all()
        return [M.from_wrapper_execution_model(m) for m in rows]


class SqlAlchemyNormalizedBatchRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, normalized_batch: NormalizedBatch) -> None:
        self._session.add(M.to_normalized_batch_model(normalized_batch))

    def get(self, normalized_batch_id: UUID) -> NormalizedBatch | None:
        m = get_model_or_pending(
            self._session, NormalizedBatchModel, "normalized_batch_id", normalized_batch_id
        )
        return M.from_normalized_batch_model(m) if m else None

    def get_by_idempotency_key(self, key: str) -> NormalizedBatch | None:
        m = self._session.scalar(
            select(NormalizedBatchModel).where(
                NormalizedBatchModel.idempotency_key == key
            )
        )
        return M.from_normalized_batch_model(m) if m else None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[NormalizedBatch]:
        rows = self._session.scalars(
            select(NormalizedBatchModel).where(
                NormalizedBatchModel.pipeline_run_id == pipeline_run_id
            )
        ).all()
        return [M.from_normalized_batch_model(m) for m in rows]
