from __future__ import annotations

from typing import Callable, ContextManager

from provenance_service.application.unit_of_work import UnitOfWork

UnitOfWorkFactory = Callable[[], ContextManager[UnitOfWork]]
