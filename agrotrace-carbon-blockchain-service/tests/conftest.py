from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from app.application.container import init_database
from app.infrastructure.db.connection import create_engine_from_settings
from app.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from app.shared.config import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    blockchain_db = tmp_path / "blockchain.db"
    provenance_db = tmp_path / "provenance.db"
    provenance_db.write_text("", encoding="utf-8")
    return Settings(
        database_url=f"sqlite:///{blockchain_db}",
        provenance_database_url=str(provenance_db),
        environment="local",
    )


@pytest.fixture
def uow_factory():
    def _make(settings: Settings) -> SqlAlchemyUnitOfWork:
        init_database(settings)
        session_factory = sessionmaker(
            bind=create_engine_from_settings(settings),
            expire_on_commit=False,
        )
        return SqlAlchemyUnitOfWork(session_factory)

    return _make
