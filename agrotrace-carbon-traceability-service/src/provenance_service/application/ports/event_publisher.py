"""Outbound port for publishing outbox events to the wider platform."""

from __future__ import annotations

from typing import Protocol

from provenance_service.domain.audit.entities import OutboxEvent


class EventPublisher(Protocol):
    """Publishes a single outbox event to a downstream transport.

    Implementations may use a logger (no-op v1), HTTP webhooks, Kafka, etc.
    Must raise on transport failure so the worker keeps the event in pending state.
    """

    def publish(self, event: OutboxEvent) -> None: ...
