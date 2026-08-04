"""Prometheus metrics exposed under ``/metrics``."""

from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

REGISTRY = CollectorRegistry(auto_describe=True)

PROVENANCE_RECORDS = Counter(
    "provenance_records_total",
    "Number of provenance records persisted, by kind and outcome.",
    labelnames=("kind", "outcome"),
    registry=REGISTRY,
)

RECORDER_DURATION = Histogram(
    "provenance_recorder_duration_seconds",
    "Duration of ProvenanceRecorder methods.",
    labelnames=("method",),
    registry=REGISTRY,
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


@contextmanager
def record_recorder_duration(method: str) -> Iterator[None]:
    start = perf_counter()
    try:
        yield
    finally:
        RECORDER_DURATION.labels(method=method).observe(perf_counter() - start)


def metrics_response() -> Response:
    payload = generate_latest(REGISTRY)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
