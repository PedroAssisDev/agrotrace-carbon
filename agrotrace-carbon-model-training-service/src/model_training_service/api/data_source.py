"""Carregamento da fonte configurada de resultados aprovados."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from model_training_service.data.csv_source import CsvApprovedResultsSource
from model_training_service.data.sparql_source import SparqlApprovedResultsSource
from model_training_service.domain.errors import DataSourceUnavailableError


def load_configured_source(
    config: dict[str, Any],
    *,
    override: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    source_cfg = dict(override or config.get("data_source") or {})
    source_type = str(source_cfg.get("type") or "csv").lower()
    meta = {"type": source_type}

    try:
        if source_type == "csv":
            path = source_cfg.get("path") or source_cfg.get("location")
            if not path:
                raise DataSourceUnavailableError("data_source.path não configurado.")
            location = Path(path)
            if not location.is_absolute():
                # relative to config file when available
                config_path = (config.get("_meta") or {}).get("config_path")
                if config_path:
                    location = (Path(config_path).parent / location).resolve()
                else:
                    location = location.resolve()
            if not location.exists():
                raise DataSourceUnavailableError(f"CSV de treinamento não encontrado: {location}")
            meta["location"] = str(location)
            frame = CsvApprovedResultsSource(
                location, separator=source_cfg.get("separator")
            ).load()
            return frame, meta

        if source_type == "sparql":
            endpoint = source_cfg.get("endpoint")
            query_file = source_cfg.get("query_file") or source_cfg.get("sparql_query")
            if not endpoint or not query_file:
                raise DataSourceUnavailableError(
                    "SPARQL exige endpoint e query_file na configuração."
                )
            query_path = Path(query_file)
            if not query_path.is_absolute():
                config_path = (config.get("_meta") or {}).get("config_path")
                if config_path:
                    query_path = (Path(config_path).parent / query_path).resolve()
            meta.update({"endpoint": endpoint, "query_file": str(query_path)})
            frame = SparqlApprovedResultsSource(endpoint, str(query_path)).load()
            return frame, meta

        raise DataSourceUnavailableError(f"Tipo de fonte não suportado: {source_type}")
    except DataSourceUnavailableError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DataSourceUnavailableError(str(exc)) from exc
