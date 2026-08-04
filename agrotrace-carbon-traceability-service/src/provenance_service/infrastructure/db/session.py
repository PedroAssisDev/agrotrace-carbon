"""SQLAlchemy engine and session factories.

Sync only. The ledger workload is dominated by short transactional writes;
async would only add complexity to the UoW without a real performance win.

SQLite: ``check_same_thread=False`` and ``PRAGMA foreign_keys=ON`` on connect.
PostgreSQL: pool sizing from settings.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import Session, sessionmaker

from provenance_service.infrastructure.config import Settings, get_settings


def database_url_is_sqlite(url: str) -> bool:
    return url.split(":", 1)[0] == "sqlite"


def ensure_sqlite_parent_dir_exists(url: str) -> None:
    """Ensure parent directory exists for file-based SQLite (e.g. ./data/provenance.db)."""

    if not database_url_is_sqlite(url):
        return
    u = make_url(url)
    if not u.database or u.database == ":memory:":
        return
    db_path = Path(u.database)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)


@event.listens_for(Engine, "connect")
def _sqlite_on_connect(dbapi_conn, _connection_record) -> None:  # type: ignore[no-untyped-def]
    try:
        import sqlite3
    except ImportError:  # pragma: no cover
        return
    if isinstance(dbapi_conn, sqlite3.Connection):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def create_engine_from_settings(settings: Settings | None = None) -> Engine:
    s = settings or get_settings()
    url = s.database_url
    ensure_sqlite_parent_dir_exists(url)
    common: dict = {"echo": s.database_echo, "future": True}
    if database_url_is_sqlite(url):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
            **common,
        )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=s.database_pool_size,
        max_overflow=s.database_max_overflow,
        **common,
    )


def create_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine_from_settings()


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return create_sessionmaker(get_engine())


def clear_engine_cache() -> None:
    """Clear cached engine/session factory (e.g. after changing ``PROV_DATABASE_URL``).

    Tests may replace ``get_engine`` / ``get_sessionmaker`` with plain callables;
    only invoke ``cache_clear`` when the ``lru_cache`` wrappers are active.
    """

    for getter in (get_engine, get_sessionmaker):
        clear = getattr(getter, "cache_clear", None)
        if clear is not None:
            clear()
