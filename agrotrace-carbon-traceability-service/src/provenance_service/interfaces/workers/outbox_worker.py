"""Standalone outbox worker process.

Run with::

    python -m provenance_service.interfaces.workers.outbox_worker

It uses the same UoW factory and stub publisher as the API process. In
production deploy this as a separate container so writes from the API and
relay decoupling can scale independently.
"""

from __future__ import annotations

import signal
import threading
import time

from provenance_service.infrastructure.adapters import LoggingEventPublisher
from provenance_service.infrastructure.config import get_settings
from provenance_service.infrastructure.observability import (
    configure_logging,
    get_logger,
)
from provenance_service.infrastructure.outbox import OutboxDispatcher, OutboxWorker
from provenance_service.interfaces.api.deps import get_uow_factory


def main() -> None:
    settings = get_settings()
    configure_logging(
        service_name=f"{settings.service_name}-outbox-worker",
        environment=settings.environment,
        level=settings.log_level,
    )
    log = get_logger("outbox.main")

    dispatcher = OutboxDispatcher(
        get_uow_factory(),
        LoggingEventPublisher(),
        batch_size=settings.outbox_batch_size,
    )
    worker = OutboxWorker(
        dispatcher,
        poll_interval_seconds=settings.outbox_poll_interval_seconds,
    )

    stop_event = threading.Event()

    def _shutdown(signum, _frame) -> None:  # type: ignore[no-untyped-def]
        log.info("outbox.signal_received", signum=signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    worker.start()
    log.info("outbox.main.running")
    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    finally:
        worker.stop()
        log.info("outbox.main.stopped")


if __name__ == "__main__":  # pragma: no cover
    main()
