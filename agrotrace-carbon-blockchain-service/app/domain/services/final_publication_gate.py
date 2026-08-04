"""Defense-in-depth gate: anchoring only after final ontology publication."""

from __future__ import annotations

from app.shared.constants import FINAL_PUBLICATION_EVENT_TYPES
from app.shared.exceptions import FinalPublicationRequiredError


def is_final_publication_event(event_type: str | None) -> bool:
    return bool(event_type) and event_type in FINAL_PUBLICATION_EVENT_TYPES


def require_final_publication_event(event_type: str | None, *, context: str = "") -> None:
    if is_final_publication_event(event_type):
        return
    suffix = f" ({context})" if context else ""
    raise FinalPublicationRequiredError(
        f"Anchoring requires a final ontology publication event; "
        f"got {event_type!r}{suffix}. Eligible: {sorted(FINAL_PUBLICATION_EVENT_TYPES)}"
    )
