"""Bootstrap, prefixes and shared constants for the full-population demo."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

os.chdir(_REPO_ROOT)
os.environ.setdefault("PROV_DATABASE_URL", "sqlite:///./data/provenance.db")

DEMO_PREFIX = "demo_repo_"
CASE_PREFIX_ANNUAL = "demo_annual_direct_"
CASE_PREFIX_MONTHLY = "demo_monthly_to_annual_"
CASE_PREFIX_DAILY = "demo_daily_to_monthly_to_annual_"
CASE_PREFIX_REVISION = "demo_revision_"

FARM_SAO_PEDRO = "Fazenda São Pedro"
FARM_BOA_VISTA = "Fazenda Boa Vista"
FARM_SANTA_CLARA = "Fazenda Santa Clara"

YEAR = "2026"

RUN_CODE_ANNUAL = f"{DEMO_PREFIX}sao_pedro_{YEAR}"
RUN_CODE_MONTHLY_PREFIX = f"{DEMO_PREFIX}boa_vista_{YEAR}"
RUN_CODE_SANTA_CLARA_PREFIX = f"{DEMO_PREFIX}santa_clara_{YEAR}"
RUN_CODE_REVISION = f"{DEMO_PREFIX}reprocessing_{YEAR}"

METHOD_CODE = "demo-repo-ghg-2026"
WRAPPER_NAME = "demo-repo-normalizer"
WRAPPER_VERSION = "1.0.0"

ONTOLOGY_NAME = "agrotrace-demo"
ONTOLOGY_VERSION = "2026.04"


def ensure_local_database() -> str:
    """Create schema + append-only triggers if missing; return database URL."""
    from provenance_service.local_db_init import main as init_db

    init_db()
    from provenance_service.infrastructure.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    return get_settings().database_url


def create_session_stack():
    """Return (engine, session_factory, settings) for demo scripts."""
    from provenance_service.infrastructure.config import get_settings
    from provenance_service.infrastructure.db.session import (
        create_engine_from_settings,
        create_sessionmaker,
    )

    get_settings.cache_clear()  # type: ignore[attr-defined]
    settings = get_settings()
    engine = create_engine_from_settings(settings)
    return engine, create_sessionmaker(engine), settings
