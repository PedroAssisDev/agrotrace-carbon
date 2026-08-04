from __future__ import annotations

from typing import Protocol

import pandas as pd


class ApprovedResultsSource(Protocol):
    def load(self) -> pd.DataFrame:
        """Load approved historical results using the canonical field names."""
