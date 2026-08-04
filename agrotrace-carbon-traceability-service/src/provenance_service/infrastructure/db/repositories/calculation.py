"""SQLAlchemy implementations of the calculation-context repositories."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from provenance_service.domain.shared.enums import CalculationResultSetStatus

from provenance_service.domain.calculation.entities import (
    CalculationExecution,
    CalculationMethod,
    CalculationMethodVersion,
    CalculationParameterSet,
    CalculationParameterValue,
    CalculationResultAggregationLink,
    CalculationResultItem,
    CalculationResultSet,
    CalculationReview,
    ResultPublicationExecution,
)
from provenance_service.infrastructure.db.models.calculation import (
    CalculationExecutionModel,
    CalculationMethodModel,
    CalculationMethodVersionModel,
    CalculationParameterSetModel,
    CalculationParameterValueModel,
    CalculationResultAggregationLinkModel,
    CalculationResultItemModel,
    CalculationResultSetModel,
    CalculationReviewModel,
    ResultPublicationExecutionModel,
)
from provenance_service.infrastructure.db.repositories import _mappers as M
from provenance_service.infrastructure.db.repositories._session_pending import (
    get_model_or_pending,
)


class SqlAlchemyCalculationMethodRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, method: CalculationMethod) -> None:
        self._session.add(M.to_calculation_method_model(method))

    def get(self, calculation_method_id: UUID) -> CalculationMethod | None:
        m = get_model_or_pending(
            self._session, CalculationMethodModel, "calculation_method_id", calculation_method_id
        )
        return M.from_calculation_method_model(m) if m else None

    def get_by_code(self, method_code: str) -> CalculationMethod | None:
        m = self._session.scalar(
            select(CalculationMethodModel).where(
                CalculationMethodModel.method_code == method_code
            )
        )
        return M.from_calculation_method_model(m) if m else None

    def list_all(self) -> list[CalculationMethod]:
        rows = self._session.scalars(select(CalculationMethodModel)).all()
        return [M.from_calculation_method_model(m) for m in rows]


class SqlAlchemyCalculationMethodVersionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, version: CalculationMethodVersion) -> None:
        self._session.add(M.to_calculation_method_version_model(version))

    def get(self, calculation_method_version_id: UUID) -> CalculationMethodVersion | None:
        m = get_model_or_pending(
            self._session,
            CalculationMethodVersionModel,
            "calculation_method_version_id",
            calculation_method_version_id,
        )
        return M.from_calculation_method_version_model(m) if m else None

    def list_by_method(
        self, calculation_method_id: UUID
    ) -> list[CalculationMethodVersion]:
        rows = self._session.scalars(
            select(CalculationMethodVersionModel).where(
                CalculationMethodVersionModel.calculation_method_id == calculation_method_id
            )
        ).all()
        return [M.from_calculation_method_version_model(m) for m in rows]


class SqlAlchemyCalculationParameterSetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, parameter_set: CalculationParameterSet) -> None:
        self._session.add(M.to_calculation_parameter_set_model(parameter_set))

    def add_value(self, value: CalculationParameterValue) -> None:
        self._session.add(M.to_calculation_parameter_value_model(value))

    def get(
        self, calculation_parameter_set_id: UUID
    ) -> CalculationParameterSet | None:
        m = get_model_or_pending(
            self._session,
            CalculationParameterSetModel,
            "calculation_parameter_set_id",
            calculation_parameter_set_id,
        )
        return M.from_calculation_parameter_set_model(m) if m else None

    def list_values(
        self, calculation_parameter_set_id: UUID
    ) -> list[CalculationParameterValue]:
        rows = self._session.scalars(
            select(CalculationParameterValueModel).where(
                CalculationParameterValueModel.calculation_parameter_set_id
                == calculation_parameter_set_id
            )
        ).all()
        return [M.from_calculation_parameter_value_model(m) for m in rows]

    def list_by_pipeline_run(
        self, pipeline_run_id: UUID
    ) -> list[CalculationParameterSet]:
        rows = self._session.scalars(
            select(CalculationParameterSetModel).where(
                CalculationParameterSetModel.pipeline_run_id == pipeline_run_id
            )
        ).all()
        return [M.from_calculation_parameter_set_model(m) for m in rows]


class SqlAlchemyCalculationExecutionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, execution: CalculationExecution) -> None:
        self._session.add(M.to_calculation_execution_model(execution))

    def get(self, calculation_execution_id: UUID) -> CalculationExecution | None:
        m = get_model_or_pending(
            self._session, CalculationExecutionModel, "calculation_execution_id", calculation_execution_id
        )
        return M.from_calculation_execution_model(m) if m else None

    def get_by_idempotency_key(self, key: str) -> CalculationExecution | None:
        m = self._session.scalar(
            select(CalculationExecutionModel).where(
                CalculationExecutionModel.idempotency_key == key
            )
        )
        return M.from_calculation_execution_model(m) if m else None

    def list_by_pipeline_run(
        self, pipeline_run_id: UUID
    ) -> list[CalculationExecution]:
        rows = self._session.scalars(
            select(CalculationExecutionModel).where(
                CalculationExecutionModel.pipeline_run_id == pipeline_run_id
            )
        ).all()
        return [M.from_calculation_execution_model(m) for m in rows]


class SqlAlchemyCalculationResultSetRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, result_set: CalculationResultSet) -> None:
        self._session.add(M.to_calculation_result_set_model(result_set))

    def add_item(self, item: CalculationResultItem) -> None:
        self._session.add(M.to_calculation_result_item_model(item))

    def get(self, calculation_result_set_id: UUID) -> CalculationResultSet | None:
        m = get_model_or_pending(
            self._session,
            CalculationResultSetModel,
            "calculation_result_set_id",
            calculation_result_set_id,
        )
        return M.from_calculation_result_set_model(m) if m else None

    def list_items(
        self, calculation_result_set_id: UUID
    ) -> list[CalculationResultItem]:
        rows = self._session.scalars(
            select(CalculationResultItemModel).where(
                CalculationResultItemModel.calculation_result_set_id
                == calculation_result_set_id
            )
        ).all()
        return [M.from_calculation_result_item_model(m) for m in rows]

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[CalculationResultSet]:
        rows = self._session.scalars(
            select(CalculationResultSetModel).where(
                CalculationResultSetModel.pipeline_run_id == pipeline_run_id
            )
        ).all()
        return [M.from_calculation_result_set_model(m) for m in rows]

    def update_status(
        self, calculation_result_set_id: UUID, status: CalculationResultSetStatus
    ) -> None:
        # Ensure the row exists in the DB before UPDATE (pending INSERT must flush first).
        self._session.flush()
        stmt = (
            update(CalculationResultSetModel)
            .where(
                CalculationResultSetModel.calculation_result_set_id
                == calculation_result_set_id
            )
            .values(result_set_status=status.value)
        )
        self._session.execute(stmt)

    def update_approved_at(
        self, calculation_result_set_id: UUID, approved_at: datetime
    ) -> None:
        self._session.flush()
        stmt = (
            update(CalculationResultSetModel)
            .where(
                CalculationResultSetModel.calculation_result_set_id
                == calculation_result_set_id
            )
            .values(approved_at=approved_at)
        )
        self._session.execute(stmt)

    def update_published_at(
        self, calculation_result_set_id: UUID, published_at: datetime
    ) -> None:
        self._session.flush()
        stmt = (
            update(CalculationResultSetModel)
            .where(
                CalculationResultSetModel.calculation_result_set_id
                == calculation_result_set_id
            )
            .values(published_at=published_at)
        )
        self._session.execute(stmt)

    def mark_superseded(self, current_id: UUID, superseded_by_id: UUID) -> None:
        # NOTE: result_set is append-only at the row level; superseded_by_id is the
        # mutable field. PostgreSQL triggers deny UPDATE unless we bypass via
        # session_replication_role; SQLite local mode has no such triggers.
        from sqlalchemy import text as sa_text

        stmt = (
            update(CalculationResultSetModel)
            .where(CalculationResultSetModel.calculation_result_set_id == current_id)
            .values(superseded_by_id=superseded_by_id)
        )
        dialect = self._session.get_bind().dialect.name
        if dialect == "postgresql":
            self._session.execute(sa_text("SET LOCAL session_replication_role = 'replica'"))
            try:
                self._session.execute(stmt)
            finally:
                self._session.execute(sa_text("SET LOCAL session_replication_role = 'origin'"))
        else:
            self._session.execute(stmt)


class SqlAlchemyCalculationReviewRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, review: CalculationReview) -> None:
        self._session.add(M.to_calculation_review_model(review))

    def get(self, calculation_review_id: UUID) -> CalculationReview | None:
        m = get_model_or_pending(
            self._session, CalculationReviewModel, "calculation_review_id", calculation_review_id
        )
        return M.from_calculation_review_model(m) if m else None

    def list_for_result_set(
        self, calculation_result_set_id: UUID
    ) -> list[CalculationReview]:
        rows = self._session.scalars(
            select(CalculationReviewModel).where(
                CalculationReviewModel.calculation_result_set_id
                == calculation_result_set_id
            )
        ).all()
        return [M.from_calculation_review_model(m) for m in rows]


class SqlAlchemyResultPublicationExecutionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, publication: ResultPublicationExecution) -> None:
        self._session.add(M.to_result_publication_execution_model(publication))

    def get(
        self, result_publication_execution_id: UUID
    ) -> ResultPublicationExecution | None:
        m = get_model_or_pending(
            self._session,
            ResultPublicationExecutionModel,
            "result_publication_execution_id",
            result_publication_execution_id,
        )
        return M.from_result_publication_execution_model(m) if m else None

    def list_by_pipeline_run(
        self, pipeline_run_id: UUID
    ) -> list[ResultPublicationExecution]:
        rows = self._session.scalars(
            select(ResultPublicationExecutionModel).where(
                ResultPublicationExecutionModel.pipeline_run_id == pipeline_run_id
            )
        ).all()
        return [M.from_result_publication_execution_model(m) for m in rows]


class SqlAlchemyCalculationResultAggregationLinkRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, link: CalculationResultAggregationLink) -> None:
        self._session.add(M.to_calculation_result_aggregation_link_model(link))

    def list_children(self, parent_result_set_id: UUID) -> list[CalculationResultAggregationLink]:
        rows = self._session.scalars(
            select(CalculationResultAggregationLinkModel).where(
                CalculationResultAggregationLinkModel.parent_result_set_id
                == parent_result_set_id
            )
        ).all()
        return [M.from_calculation_result_aggregation_link_model(m) for m in rows]

    def list_parents(self, child_result_set_id: UUID) -> list[CalculationResultAggregationLink]:
        rows = self._session.scalars(
            select(CalculationResultAggregationLinkModel).where(
                CalculationResultAggregationLinkModel.child_result_set_id
                == child_result_set_id
            )
        ).all()
        return [M.from_calculation_result_aggregation_link_model(m) for m in rows]
