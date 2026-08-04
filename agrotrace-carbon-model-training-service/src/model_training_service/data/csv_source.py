from __future__ import annotations

from pathlib import Path

import pandas as pd


class CsvApprovedResultsSource:
    def __init__(self, path: str | Path, separator: str | None = None) -> None:
        self.path = Path(path)
        self.separator = separator

    def load(self) -> pd.DataFrame:
        if not self.path.exists():
            raise FileNotFoundError(f"CSV não encontrado: {self.path}")
        if self.separator:
            return pd.read_csv(self.path, sep=self.separator)
        return pd.read_csv(self.path, sep=None, engine="python")
