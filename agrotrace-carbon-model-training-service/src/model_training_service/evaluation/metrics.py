from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def regression_metrics(y_true, y_pred) -> dict[str, float | None]:
    y_true_array = np.asarray(y_true, dtype=float)
    y_pred_array = np.asarray(y_pred, dtype=float)
    metrics: dict[str, float | None] = {
        "mae": float(mean_absolute_error(y_true_array, y_pred_array)),
        "rmse": float(math.sqrt(mean_squared_error(y_true_array, y_pred_array))),
        "r2": None,
        "mape": None,
    }
    if len(y_true_array) >= 2 and not np.allclose(y_true_array, y_true_array[0]):
        metrics["r2"] = float(r2_score(y_true_array, y_pred_array))
    nonzero = np.abs(y_true_array) > 1e-12
    if nonzero.any():
        metrics["mape"] = float(
            np.mean(np.abs((y_true_array[nonzero] - y_pred_array[nonzero]) / y_true_array[nonzero]))
            * 100
        )
    return metrics
