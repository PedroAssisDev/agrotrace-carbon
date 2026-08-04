"""Alembic environment configuration (PostgreSQL multi-schema migrations).

**Local prototype:** the default database is SQLite; use
``provenance-init-local-db`` or ``python scripts/init_local_db.py`` which call
``Base.metadata.create_all`` — Alembic is **not** applied for that path.

These revisions target PostgreSQL (schemas, ``JSONB``, triggers). To run them,
set ``PROV_DATABASE_URL`` to a PostgreSQL URL and install the optional
``postgres`` dependency group (``pip install -e ".[postgres]"``).

The version table lives in the ``audit`` schema so that operational
infrastructure metadata is co-located with the auditing context.
We include all schemas in autogenerate so that cross-schema FKs are detected.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from provenance_service.infrastructure.config import get_settings
from provenance_service.infrastructure.db import Base, create_engine_from_settings
from provenance_service.infrastructure.db import models as _models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

INCLUDED_SCHEMAS: tuple[str, ...] = (
    "pipeline",
    "prov_core",
    "semantic",
    "calculation",
    "audit",
    "reporting",
)


def include_object(obj, name, type_, reflected, compare_to):  # type: ignore[no-untyped-def]
    if type_ == "schema":
        return name in INCLUDED_SCHEMAS
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table="alembic_version",
        version_table_schema="audit",
        include_schemas=True,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine_from_settings(settings)
    try:
        with engine.connect() as connection:
            connection.execution_options(isolation_level="AUTOCOMMIT")
            connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS audit")

        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                version_table="alembic_version",
                version_table_schema="audit",
                include_schemas=True,
                include_object=include_object,
                compare_type=True,
                compare_server_default=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
