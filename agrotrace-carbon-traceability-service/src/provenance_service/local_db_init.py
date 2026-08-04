"""Initialize local SQLite schema (``create_all``). Used by CLI and ``scripts/init_local_db.py``."""

from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> None:
    os.chdir(_ROOT)
    os.environ.setdefault("PROV_DATABASE_URL", "sqlite:///./data/provenance.db")

    from sqlalchemy.engine.url import make_url

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

    clear_engine_cache()
    get_settings.cache_clear()  # type: ignore[attr-defined]

    settings = get_settings()
    url = settings.database_url

    if url.startswith("sqlite"):
        u = make_url(url)
        if u.database and u.database != ":memory:":
            db_path = Path(u.database)
            if not db_path.is_absolute():
                db_path = _ROOT / db_path
            db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine_from_settings()
    Base.metadata.create_all(engine)
    if url.startswith("sqlite"):
        from provenance_service.infrastructure.db.sqlite_append_only import (
            install_sqlite_append_only,
        )

        with engine.begin() as conn:
            install_sqlite_append_only(conn)
    engine.dispose()
    print(f"Local database initialized: {url}")
