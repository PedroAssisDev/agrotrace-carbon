from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.utils.validation import check_X_y, check_array, check_is_fitted


class MeanPerCowRegressor(RegressorMixin, BaseEstimator):
    """Baseline: target médio por vaca multiplicado pela quantidade de vacas."""

    def fit(self, X, y):
        X_checked, y_checked = check_X_y(X, y, ensure_2d=True, dtype=float)
        cows = X_checked[:, 0]
        valid = cows > 0
        if valid.any():
            self.mean_per_cow_ = float(np.mean(y_checked[valid] / cows[valid]))
            self.fallback_mean_ = float(np.mean(y_checked))
        else:
            self.mean_per_cow_ = 0.0
            self.fallback_mean_ = float(np.mean(y_checked))
        return self

    def predict(self, X):
        check_is_fitted(self, ["mean_per_cow_", "fallback_mean_"])
        X_checked = check_array(X, ensure_2d=True, dtype=float)
        cows = X_checked[:, 0]
        predictions = cows * self.mean_per_cow_
        return np.where(cows > 0, predictions, self.fallback_mean_)
