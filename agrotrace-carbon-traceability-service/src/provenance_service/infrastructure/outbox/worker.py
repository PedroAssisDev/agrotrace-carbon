"""Background worker that drives :class:`OutboxDispatcher` on a schedule."""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from provenance_service.infrastructure.observability import get_logger
from provenance_service.infrastructure.outbox.publisher import OutboxDispatcher


class OutboxWorker:
    def __init__(
        self,
        dispatcher: OutboxDispatcher,
        *,
        poll_interval_seconds: float = 5.0,
    ) -> None:
        self._dispatcher = dispatcher
        self._poll_interval_seconds = poll_interval_seconds
        self._scheduler: BackgroundScheduler | None = None
        self._log = get_logger("outbox.worker")

    def start(self) -> None:
        if self._scheduler is not None:
            return
        scheduler = BackgroundScheduler(timezone="UTC")
        scheduler.add_job(
            self._tick,
            trigger="interval",
            seconds=self._poll_interval_seconds,
            id="outbox-dispatch",
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        self._scheduler = scheduler
        self._log.info("outbox.worker.started", poll_interval=self._poll_interval_seconds)

    def stop(self) -> None:
        if self._scheduler is None:
            return
        self._scheduler.shutdown(wait=False)
        self._scheduler = None
        self._log.info("outbox.worker.stopped")

    def _tick(self) -> None:
        try:
            summary = self._dispatcher.dispatch_once()
            if summary.fetched:
                self._log.info(
                    "outbox.dispatch",
                    fetched=summary.fetched,
                    published=summary.published,
                    failed=summary.failed,
                )
        except Exception:  # noqa: BLE001
            self._log.exception("outbox.tick_failed")
