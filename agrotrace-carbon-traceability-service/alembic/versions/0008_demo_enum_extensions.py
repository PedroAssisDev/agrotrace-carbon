"""Extend enums for demo scenario (approved parameters, canonical_input stage).

Revision ID: 0008_demo_enum_extensions
Revises: 0007_audit_appendonly
Create Date: 2026-04-30
"""

from __future__ import annotations

from alembic import op

revision = "0008_demo_enum_extensions"
down_revision = "0007_audit_appendonly"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE parameter_set_status ADD VALUE IF NOT EXISTS 'approved'")
    op.execute("ALTER TYPE publication_stage ADD VALUE IF NOT EXISTS 'canonical_input'")


def downgrade() -> None:
    # PostgreSQL cannot remove enum values safely; no-op downgrade.
    pass
