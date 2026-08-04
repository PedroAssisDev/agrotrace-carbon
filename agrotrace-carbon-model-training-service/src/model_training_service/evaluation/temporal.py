from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TemporalFold:
    train_end: int
    test_end: int


def build_temporal_folds(
    observation_count: int,
    horizon: int,
    minimum_train_size: int,
    max_folds: int,
) -> list[TemporalFold]:
    if observation_count < minimum_train_size + horizon:
        return []

    latest_origin = observation_count - horizon
    earliest_origin = max(minimum_train_size, latest_origin - horizon * (max_folds - 1))
    origins = list(range(earliest_origin, latest_origin + 1, horizon))
    return [TemporalFold(train_end=origin, test_end=origin + horizon) for origin in origins]
