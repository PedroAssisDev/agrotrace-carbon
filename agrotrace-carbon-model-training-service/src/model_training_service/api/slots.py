"""Slots lógicos canônicos (4 regressões globais + 2 séries da propriedade)."""

from __future__ import annotations

from model_training_service.api.contracts import ModelSlot
from model_training_service.domain.enums import (
    Granularity,
    ModelFamily,
    ModelScope,
    Target,
)
from model_training_service.domain.errors import InvalidTrainingRequestError

REGRESSION_TARGETS = (Target.MILK_PRODUCTION.value, Target.TOTAL_EMISSIONS.value)
REGRESSION_GRANULARITIES = (Granularity.MONTHLY.value, Granularity.ANNUAL.value)
TS_TARGETS = REGRESSION_TARGETS


def property_model_slots(property_id: str) -> list[ModelSlot]:
    slots: list[ModelSlot] = []
    for granularity in REGRESSION_GRANULARITIES:
        for target in REGRESSION_TARGETS:
            slots.append(
                ModelSlot(
                    family=ModelFamily.REGRESSION.value,
                    scope=ModelScope.GLOBAL.value,
                    granularity=granularity,
                    target=target,
                    property_id=None,
                )
            )
    for target in TS_TARGETS:
        slots.append(
            ModelSlot(
                family=ModelFamily.TIME_SERIES.value,
                scope=ModelScope.PROPERTY.value,
                granularity=Granularity.MONTHLY.value,
                target=target,
                property_id=str(property_id),
            )
        )
    return slots


def validate_slot(slot: ModelSlot, *, expected_property_id: str | None = None) -> None:
    if slot.family == ModelFamily.REGRESSION.value:
        if slot.scope != ModelScope.GLOBAL.value:
            raise InvalidTrainingRequestError("Regressão deve ter escopo global.")
        if slot.property_id not in (None, ""):
            raise InvalidTrainingRequestError(
                "Regressão não pode ser específica por propriedade."
            )
        if slot.granularity not in REGRESSION_GRANULARITIES:
            raise InvalidTrainingRequestError(f"Granularidade inválida: {slot.granularity}")
        if slot.target not in REGRESSION_TARGETS:
            raise InvalidTrainingRequestError(f"Target inválido: {slot.target}")
        return

    if slot.family == ModelFamily.TIME_SERIES.value:
        if slot.scope != ModelScope.PROPERTY.value:
            raise InvalidTrainingRequestError("Série temporal deve ter escopo property.")
        if slot.granularity != Granularity.MONTHLY.value:
            raise InvalidTrainingRequestError("Série temporal anual não é permitida.")
        if not slot.property_id:
            raise InvalidTrainingRequestError("Série temporal exige property_id.")
        if expected_property_id and str(slot.property_id) != str(expected_property_id):
            raise InvalidTrainingRequestError(
                "property_id do slot diverge da solicitação."
            )
        if slot.target not in TS_TARGETS:
            raise InvalidTrainingRequestError(f"Target inválido: {slot.target}")
        return

    raise InvalidTrainingRequestError(f"Família inválida: {slot.family}")


def validate_request_slots(property_id: str, slots: list[ModelSlot]) -> None:
    if not property_id or not str(property_id).strip():
        raise InvalidTrainingRequestError("property_id é obrigatório.")
    if not slots:
        raise InvalidTrainingRequestError("Nenhum modelo selecionado.")
    seen: set[str] = set()
    for slot in slots:
        validate_slot(slot, expected_property_id=property_id)
        key = slot.logical_key()
        if key in seen:
            raise InvalidTrainingRequestError(f"Slot duplicado: {key}")
        seen.add(key)
