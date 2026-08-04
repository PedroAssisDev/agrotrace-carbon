"""SQLAlchemy 2.0 ORM models.

All models are imported here so that ``Base.metadata`` knows about every table
when Alembic autogenerates migrations.
"""

from provenance_service.infrastructure.db.models import (  # noqa: F401
    audit,
    base,
    calculation,
    pipeline,
    prov_core,
    reporting,
    semantic,
)
from provenance_service.infrastructure.db.models.base import Base, metadata

__all__ = ["Base", "metadata"]
