"""Identifier generation.

We use UUID v7 (time-ordered) to keep ledger inserts naturally chronological,
which improves index locality and makes manual log inspection easier than
random v4 ids. Falls back to v4 if ``uuid_utils`` is not available, which
keeps the domain layer importable even in stripped-down environments.
"""

from __future__ import annotations

import uuid

try:  # pragma: no cover - import guard
    import uuid_utils  # type: ignore[import-untyped]

    def new_uuid7() -> uuid.UUID:
        """Return a freshly generated UUID v7 as a stdlib :class:`uuid.UUID`."""
        return uuid.UUID(str(uuid_utils.uuid7()))
except ImportError:  # pragma: no cover - fallback path

    def new_uuid7() -> uuid.UUID:
        return uuid.uuid4()
