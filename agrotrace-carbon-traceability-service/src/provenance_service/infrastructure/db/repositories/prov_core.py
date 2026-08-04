"""SQLAlchemy implementations of the prov_core-context repositories."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, aliased

from provenance_service.domain.prov_core.entities import (
    ProvActivity,
    ProvAgent,
    ProvAttribute,
    ProvBundle,
    ProvEntity,
)
from provenance_service.domain.prov_core.relations import (
    ProvAssociatedWith,
    ProvDerivedFrom,
    ProvGenerated,
    ProvRevision,
    ProvUsed,
)
from provenance_service.domain.shared.enums import ProvBundleStatus
from provenance_service.domain.shared.time import utcnow
from provenance_service.infrastructure.db.models.prov_core import (
    ProvActivityModel,
    ProvAgentModel,
    ProvAssociatedWithModel,
    ProvAttributeModel,
    ProvBundleModel,
    ProvDerivedFromModel,
    ProvEntityModel,
    ProvGeneratedModel,
    ProvRevisionModel,
    ProvUsedModel,
)
from provenance_service.infrastructure.db.repositories import _mappers as M
from provenance_service.infrastructure.db.repositories._session_pending import (
    get_model_or_pending,
)


class SqlAlchemyProvBundleRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, bundle: ProvBundle) -> None:
        self._session.add(M.to_prov_bundle_model(bundle))

    def get(self, bundle_id: UUID) -> ProvBundle | None:
        m = get_model_or_pending(self._session, ProvBundleModel, "bundle_id", bundle_id)
        return M.from_prov_bundle_model(m) if m else None

    def list_by_pipeline_run(self, pipeline_run_id: UUID) -> list[ProvBundle]:
        rows = list(
            self._session.scalars(
                select(ProvBundleModel).where(
                    ProvBundleModel.pipeline_run_id == pipeline_run_id
                )
            ).all()
        )
        seen = {m.bundle_id for m in rows}
        for obj in self._session.new:
            if (
                isinstance(obj, ProvBundleModel)
                and obj.pipeline_run_id == pipeline_run_id
                and obj.bundle_id not in seen
            ):
                rows.append(obj)
                seen.add(obj.bundle_id)
        return [M.from_prov_bundle_model(m) for m in rows]

    def close(self, bundle_id: UUID) -> None:
        stmt = (
            update(ProvBundleModel)
            .where(ProvBundleModel.bundle_id == bundle_id)
            .values(status=ProvBundleStatus.CLOSED.value, closed_at=utcnow())
        )
        self._session.execute(stmt)


class SqlAlchemyProvEntityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, entity: ProvEntity) -> None:
        self._session.add(M.to_prov_entity_model(entity))

    def get(self, entity_id: UUID) -> ProvEntity | None:
        m = get_model_or_pending(self._session, ProvEntityModel, "entity_id", entity_id)
        return M.from_prov_entity_model(m) if m else None

    def list_by_bundle(self, bundle_id: UUID) -> list[ProvEntity]:
        rows = self._session.scalars(
            select(ProvEntityModel).where(ProvEntityModel.bundle_id == bundle_id)
        ).all()
        return [M.from_prov_entity_model(m) for m in rows]

    def invalidate(self, entity_id: UUID) -> None:
        # invalidated_at is part of the immutable record's design; we set it once.
        stmt = (
            update(ProvEntityModel)
            .where(
                ProvEntityModel.entity_id == entity_id,
                ProvEntityModel.invalidated_at.is_(None),
            )
            .values(invalidated_at=utcnow())
        )
        self._session.execute(stmt)


class SqlAlchemyProvActivityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, activity: ProvActivity) -> None:
        self._session.add(M.to_prov_activity_model(activity))

    def get(self, activity_id: UUID) -> ProvActivity | None:
        m = get_model_or_pending(self._session, ProvActivityModel, "activity_id", activity_id)
        return M.from_prov_activity_model(m) if m else None

    def list_by_bundle(self, bundle_id: UUID) -> list[ProvActivity]:
        rows = self._session.scalars(
            select(ProvActivityModel).where(ProvActivityModel.bundle_id == bundle_id)
        ).all()
        return [M.from_prov_activity_model(m) for m in rows]


class SqlAlchemyProvAgentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, agent: ProvAgent) -> None:
        self._session.add(M.to_prov_agent_model(agent))

    def get(self, agent_id: UUID) -> ProvAgent | None:
        m = get_model_or_pending(self._session, ProvAgentModel, "agent_id", agent_id)
        return M.from_prov_agent_model(m) if m else None

    def get_by_external_reference(self, external_reference: str) -> ProvAgent | None:
        m = self._session.scalar(
            select(ProvAgentModel).where(
                ProvAgentModel.external_reference == external_reference
            )
        )
        return M.from_prov_agent_model(m) if m else None


class SqlAlchemyProvRelationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add_used(self, relation: ProvUsed) -> None:
        self._session.add(M.to_prov_used_model(relation))

    def add_generated(self, relation: ProvGenerated) -> None:
        self._session.add(M.to_prov_generated_model(relation))

    def add_derived_from(self, relation: ProvDerivedFrom) -> None:
        self._session.add(M.to_prov_derived_from_model(relation))

    def add_associated_with(self, relation: ProvAssociatedWith) -> None:
        self._session.add(M.to_prov_associated_with_model(relation))

    def add_revision(self, revision: ProvRevision) -> None:
        self._session.add(M.to_prov_revision_model(revision))

    def list_used_by_activity(self, activity_id: UUID) -> list[ProvUsed]:
        rows = self._session.scalars(
            select(ProvUsedModel).where(ProvUsedModel.activity_id == activity_id)
        ).all()
        return [M.from_prov_used_model(m) for m in rows]

    def list_generated_by_activity(self, activity_id: UUID) -> list[ProvGenerated]:
        rows = self._session.scalars(
            select(ProvGeneratedModel).where(ProvGeneratedModel.activity_id == activity_id)
        ).all()
        return [M.from_prov_generated_model(m) for m in rows]

    def list_derived_for_entity(self, entity_id: UUID) -> list[ProvDerivedFrom]:
        rows = self._session.scalars(
            select(ProvDerivedFromModel).where(
                ProvDerivedFromModel.generated_entity_id == entity_id
            )
        ).all()
        return [M.from_prov_derived_from_model(m) for m in rows]

    def list_derived_for_pipeline_run(self, pipeline_run_id: UUID) -> list[ProvDerivedFrom]:
        rows = self._session.scalars(
            select(ProvDerivedFromModel)
            .join(
                ProvEntityModel,
                ProvDerivedFromModel.generated_entity_id == ProvEntityModel.entity_id,
            )
            .where(ProvEntityModel.pipeline_run_id == pipeline_run_id)
        ).all()
        return [M.from_prov_derived_from_model(m) for m in rows]

    def list_revisions_for_pipeline_run(self, pipeline_run_id: UUID) -> list[ProvRevision]:
        pe_prev = aliased(ProvEntityModel)
        pe_new = aliased(ProvEntityModel)
        rows = self._session.scalars(
            select(ProvRevisionModel)
            .join(pe_prev, ProvRevisionModel.previous_entity_id == pe_prev.entity_id)
            .join(pe_new, ProvRevisionModel.new_entity_id == pe_new.entity_id)
            .where(
                (pe_prev.pipeline_run_id == pipeline_run_id)
                | (pe_new.pipeline_run_id == pipeline_run_id)
            )
        ).all()
        return [M.from_prov_revision_model(m) for m in rows]

    def list_associations_for_activity(
        self, activity_id: UUID
    ) -> list[ProvAssociatedWith]:
        rows = self._session.scalars(
            select(ProvAssociatedWithModel).where(
                ProvAssociatedWithModel.activity_id == activity_id
            )
        ).all()
        return [M.from_prov_associated_with_model(m) for m in rows]


class SqlAlchemyProvAttributeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, attribute: ProvAttribute) -> None:
        self._session.add(M.to_prov_attribute_model(attribute))

    def list_for_entity(self, entity_id: UUID) -> list[ProvAttribute]:
        rows = self._session.scalars(
            select(ProvAttributeModel).where(ProvAttributeModel.entity_id == entity_id)
        ).all()
        return [M.from_prov_attribute_model(m) for m in rows]

    def list_for_activity(self, activity_id: UUID) -> list[ProvAttribute]:
        rows = self._session.scalars(
            select(ProvAttributeModel).where(ProvAttributeModel.activity_id == activity_id)
        ).all()
        return [M.from_prov_attribute_model(m) for m in rows]

    def list_for_agent(self, agent_id: UUID) -> list[ProvAttribute]:
        rows = self._session.scalars(
            select(ProvAttributeModel).where(ProvAttributeModel.agent_id == agent_id)
        ).all()
        return [M.from_prov_attribute_model(m) for m in rows]
