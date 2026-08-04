from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.connection import create_engine_from_settings, create_session_factory
from app.infrastructure.db.models import Base
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.infrastructure.anchoring.providers_registry import ProvidersRegistry
from app.infrastructure.provenance.sqlite_provenance_event_reader import (
    SQLiteProvenanceDataReader,
    SQLiteProvenanceEventReader,
)
from app.shared.config import Settings, get_settings


def init_database(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    engine = create_engine_from_settings(settings)
    Base.metadata.create_all(engine)
    with SqlAlchemyUnitOfWork(create_session_factory(settings)) as uow:
        uow.blockchain_networks.ensure_default_networks()


class ServiceContainer:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.session_factory = create_session_factory(self.settings)
        self.event_reader = SQLiteProvenanceEventReader(self.settings)
        self.data_reader = SQLiteProvenanceDataReader(self.settings)
        self.providers = ProvidersRegistry()

    def unit_of_work(self) -> SqlAlchemyUnitOfWork:
        return SqlAlchemyUnitOfWork(self.session_factory)
