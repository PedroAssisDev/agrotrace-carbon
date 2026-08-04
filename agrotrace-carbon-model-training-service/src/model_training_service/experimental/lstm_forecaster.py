"""LSTM univariada opcional.

Este arquivo adapta o esboço original ao escopo atual: somente a própria variável-alvo é usada,
sem vacas em lactação ou qualquer variável exógena. A LSTM não participa da seleção padrão porque
séries curtas geralmente não oferecem dados suficientes para esse tipo de rede.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.preprocessing import MinMaxScaler


def create_univariate_sequences(values: np.ndarray, lookback: int) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for index in range(len(values) - lookback):
        X.append(values[index : index + lookback])
        y.append(values[index + lookback])
    return np.asarray(X), np.asarray(y)


@dataclass
class ExperimentalLSTMForecaster:
    lookback: int = 6
    units: int = 32
    epochs: int = 50
    batch_size: int = 8

    def fit(self, values: np.ndarray):
        try:
            from tensorflow.keras import Sequential
            from tensorflow.keras.layers import Dense, Input, LSTM
        except ImportError as exc:
            raise RuntimeError(
                "Instale o extra opcional com: pip install -e '.[lstm]'"
            ) from exc

        self.scaler_ = MinMaxScaler()
        scaled = self.scaler_.fit_transform(np.asarray(values, dtype=float).reshape(-1, 1)).ravel()
        X, y = create_univariate_sequences(scaled, self.lookback)
        if len(X) < 8:
            raise ValueError("A LSTM exige mais sequências de treinamento.")
        X = X.reshape((X.shape[0], X.shape[1], 1))
        self.model_ = Sequential(
            [
                Input(shape=(self.lookback, 1)),
                LSTM(self.units),
                Dense(1),
            ]
        )
        self.model_.compile(optimizer="adam", loss="mean_squared_error")
        self.model_.fit(
            X,
            y,
            epochs=self.epochs,
            batch_size=min(self.batch_size, len(X)),
            verbose=0,
            validation_split=0.1 if len(X) >= 20 else 0.0,
        )
        self.last_window_ = scaled[-self.lookback :].copy()
        return self

    def forecast(self, horizon: int) -> np.ndarray:
        window = self.last_window_.copy().tolist()
        predictions = []
        for _ in range(horizon):
            X = np.asarray(window[-self.lookback :]).reshape(1, self.lookback, 1)
            value = float(self.model_.predict(X, verbose=0).ravel()[0])
            predictions.append(value)
            window.append(value)
        return self.scaler_.inverse_transform(np.asarray(predictions).reshape(-1, 1)).ravel()
