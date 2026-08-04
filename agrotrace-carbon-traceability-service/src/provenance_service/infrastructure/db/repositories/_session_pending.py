"""Resolve ORM rows still in ``Session.new`` (SQLite + Uuid PK: ``Session.get`` can miss)."""

from __future__ import annotations

from typing import TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

T = TypeVar("T")


def get_model_or_pending(
    session: Session, model_cls: type[T], pk_attr: str, pk: UUID
) -> T | None:
    m = session.get(model_cls, pk)
    if m is not None:
        return m
    for pending in session.new:
        if isinstance(pending, model_cls) and getattr(pending, pk_attr) == pk:
            return pending
    return None
