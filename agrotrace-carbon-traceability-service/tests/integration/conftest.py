"""Integration fixtures using SQLite (shared temp file by default).

No Docker or testcontainers. Uses a session-scoped SQLite file so code that
creates its own engine (e.g. ``seed_demo_full_pipeline_001.main``) still sees
the same database as the test fixtures.

Resets schema between tests via ``drop_all`` / ``create_all``.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def sqlite_url(tmp_path_factory: pytest.TempPathFactory) -> str:
    override = os.getenv("PROV_TEST_DATABASE_URL")
    if override:
        return override
    db_path = tmp_path_factory.mktemp("provenance_sqlite") / "integration.sqlite"
    return f"sqlite:///{db_path.resolve().as_posix()}"


@pytest.fixture(scope="session")
def engine(sqlite_url: str) -> Iterator[Engine]:
    os.environ["PROV_DATABASE_URL"] = sqlite_url
    os.chdir(ROOT_DIR)

    from provenance_service.infrastructure.config import get_settings
    from provenance_service.infrastructure.db import Base, clear_engine_cache
    from provenance_service.infrastructure.db.models import (  # noqa: F401
        audit,
        calculation,
        pipeline,
        prov_core,
        reporting,
        semantic,
    )
    from provenance_service.infrastructure.db.session import create_engine_from_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    clear_engine_cache()

    eng = create_engine_from_settings()
    Base.metadata.create_all(eng)
    if eng.dialect.name == "sqlite":
        from provenance_service.infrastructure.db.sqlite_append_only import (
            install_sqlite_append_only,
        )

        with eng.begin() as conn:
            install_sqlite_append_only(conn)
    yield eng
    eng.dispose()
    clear_engine_cache()


@pytest.fixture()
def db_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _reset_schema_between_tests(engine: Engine) -> Iterator[None]:
    from provenance_service.infrastructure.db import Base

    yield
    if engine.dialect.name == "sqlite":
        from provenance_service.infrastructure.db.sqlite_append_only import (
            drop_sqlite_append_only,
            install_sqlite_append_only,
        )

        with engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys=OFF"))
            conn.commit()
            drop_sqlite_append_only(conn)
            conn.commit()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with engine.begin() as conn:
            conn.execute(text("PRAGMA foreign_keys=ON"))
            install_sqlite_append_only(conn)
    else:
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)


@pytest.fixture()
def uow_factory(db_session_factory: sessionmaker[Session]):
    from contextlib import contextmanager

    from provenance_service.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

    @contextmanager
    def _factory():
        with SqlAlchemyUnitOfWork(db_session_factory) as uow:
            yield uow

    return _factory


@pytest.fixture()
def recorder():
    from provenance_service.application.services.provenance_recorder import ProvenanceRecorder

    return ProvenanceRecorder()
