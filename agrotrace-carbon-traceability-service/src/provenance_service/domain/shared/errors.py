"""Domain errors. The application/interfaces layers translate these to HTTP."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-level errors."""

    code: str = "domain_error"

    def __init__(self, message: str, *, details: dict[str, object] | None = None) -> None:
        super().__init__(message)
        self.details: dict[str, object] = dict(details or {})


class InvariantViolationError(DomainError):
    """A business invariant has been violated."""

    code = "invariant_violation"


class NotFoundError(DomainError):
    """An expected aggregate could not be found."""

    code = "not_found"


class AlreadyExistsError(DomainError):
    """An aggregate with the given key already exists."""

    code = "already_exists"


class IdempotencyConflictError(DomainError):
    """A second request reused an idempotency key with a different payload."""

    code = "idempotency_conflict"


class AppendOnlyViolationError(DomainError):
    """An attempt to mutate an append-only record was caught at application level."""

    code = "append_only_violation"
