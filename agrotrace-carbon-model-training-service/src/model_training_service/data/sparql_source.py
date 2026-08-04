from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests


class SparqlApprovedResultsSource:
    """Generic SPARQL source.

    The query must expose variables using the canonical field names expected by the module.
    """

    def __init__(
        self,
        endpoint: str,
        query_file: str | Path,
        timeout_seconds: int = 60,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.query_file = Path(query_file)
        self.timeout_seconds = timeout_seconds
        self.headers = headers or {}

    def load(self) -> pd.DataFrame:
        if not self.query_file.exists():
            raise FileNotFoundError(f"Consulta SPARQL não encontrada: {self.query_file}")
        query = self.query_file.read_text(encoding="utf-8")
        request_headers = {
            "Accept": "application/sparql-results+json",
            **self.headers,
        }
        response = requests.post(
            self.endpoint,
            data={"query": query},
            headers=request_headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        variables = payload.get("head", {}).get("vars", [])
        bindings = payload.get("results", {}).get("bindings", [])
        rows = []
        for binding in bindings:
            rows.append({name: binding.get(name, {}).get("value") for name in variables})
        return pd.DataFrame(rows, columns=variables)
