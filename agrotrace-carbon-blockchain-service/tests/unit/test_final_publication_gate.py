from __future__ import annotations

import pytest

from app.domain.services.final_publication_gate import (
    is_final_publication_event,
    require_final_publication_event,
)
from app.shared.constants import ELIGIBLE_ANCHOR_EVENT_TYPES
from app.shared.exceptions import FinalPublicationRequiredError


def test_final_publication_events_are_eligible() -> None:
    assert "FINAL_ONTOLOGY_PUBLISHED" in ELIGIBLE_ANCHOR_EVENT_TYPES
    assert "APPROVED_RESULT_PUBLISHED" in ELIGIBLE_ANCHOR_EVENT_TYPES
    assert "APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY" in ELIGIBLE_ANCHOR_EVENT_TYPES


def test_calculation_approved_not_eligible() -> None:
    assert "CALCULATION_APPROVED" not in ELIGIBLE_ANCHOR_EVENT_TYPES
    assert not is_final_publication_event("CALCULATION_APPROVED")


def test_require_final_publication_rejects_preliminary() -> None:
    with pytest.raises(FinalPublicationRequiredError):
        require_final_publication_event("CALCULATION_APPROVED")


def test_require_final_publication_accepts_final() -> None:
    require_final_publication_event("FINAL_ONTOLOGY_PUBLISHED")
