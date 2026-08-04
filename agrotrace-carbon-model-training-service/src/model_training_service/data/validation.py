from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from model_training_service.data.schema import (
    CANONICAL_COLUMNS,
    COLUMN_ALIASES,
    OPTIONAL_CONTROL_COLUMNS,
)
from model_training_service.domain.errors import DataValidationError
from model_training_service.domain.enums import Granularity


def normalize_approved_results(
    raw: pd.DataFrame,
    approved_values: Iterable[str] = ("approved", "aprovado"),
    published_values: Iterable[str] = ("published", "publicado"),
    duplicate_policy: str = "reject",
) -> pd.DataFrame:
    if raw.empty:
        raise DataValidationError("A fonte de dados não retornou registros.")

    data = raw.rename(columns={key: value for key, value in COLUMN_ALIASES.items() if key in raw})
    missing = [column for column in CANONICAL_COLUMNS if column not in data.columns]
    if missing:
        raise DataValidationError(f"Colunas canônicas ausentes: {missing}")

    data = data.copy()
    data["property_id"] = data["property_id"].astype(str).str.strip()
    data["granularity"] = data["granularity"].astype(str).str.strip().str.lower()

    valid_granularities = {item.value for item in Granularity}
    invalid_granularities = sorted(set(data["granularity"].dropna()) - valid_granularities)
    if invalid_granularities:
        raise DataValidationError(
            f"Granularidades inválidas: {invalid_granularities}. Use monthly ou annual."
        )

    if "approval_status" in data.columns:
        accepted = {str(value).lower() for value in approved_values}
        data = data[data["approval_status"].astype(str).str.lower().isin(accepted)]
    if "publication_status" in data.columns:
        accepted = {str(value).lower() for value in published_values}
        data = data[data["publication_status"].astype(str).str.lower().isin(accepted)]

    if data.empty:
        raise DataValidationError("Nenhum registro aprovado e publicado permaneceu após o filtro.")

    data["period"] = pd.to_datetime(data["period"], errors="coerce")
    if data["period"].isna().any():
        rows = data.index[data["period"].isna()].tolist()[:10]
        raise DataValidationError(f"Períodos inválidos nas linhas: {rows}")

    monthly_mask = data["granularity"].eq(Granularity.MONTHLY.value)
    annual_mask = data["granularity"].eq(Granularity.ANNUAL.value)
    data.loc[monthly_mask, "period"] = data.loc[monthly_mask, "period"].dt.to_period("M").dt.to_timestamp()
    data.loc[annual_mask, "period"] = data.loc[annual_mask, "period"].dt.to_period("Y").dt.to_timestamp()

    numeric_columns = [
        "lactating_cows",
        "milk_production_liters",
        "total_ghg_emissions_tco2e",
    ]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    invalid_property = data["property_id"].eq("") | data["property_id"].str.lower().eq("nan")
    if invalid_property.any():
        raise DataValidationError("Existem registros sem property_id válido.")

    if data["lactating_cows"].isna().any():
        raise DataValidationError("A coluna lactating_cows possui valores ausentes ou inválidos.")

    negative_mask = data[numeric_columns].lt(0).any(axis=1)
    if negative_mask.any():
        rows = data.index[negative_mask].tolist()[:10]
        raise DataValidationError(f"Valores negativos não são permitidos. Linhas: {rows}")

    duplicate_keys = ["property_id", "period", "granularity"]
    duplicated = data.duplicated(duplicate_keys, keep=False)
    if duplicated.any():
        if duplicate_policy == "reject":
            sample = data.loc[duplicated, duplicate_keys].head(10).to_dict("records")
            raise DataValidationError(f"Períodos duplicados encontrados: {sample}")
        if duplicate_policy == "keep_last":
            data = data.sort_index().drop_duplicates(duplicate_keys, keep="last")
        else:
            raise DataValidationError(f"duplicate_policy não suportada: {duplicate_policy}")

    ordered_columns = CANONICAL_COLUMNS + [
        column for column in OPTIONAL_CONTROL_COLUMNS if column in data.columns
    ]
    data = data[ordered_columns].sort_values(
        ["granularity", "property_id", "period"]
    ).reset_index(drop=True)

    # Convert pandas extension values to regular numeric values when possible.
    data["lactating_cows"] = data["lactating_cows"].astype(float)
    for target in ["milk_production_liters", "total_ghg_emissions_tco2e"]:
        data[target] = data[target].replace([np.inf, -np.inf], np.nan).astype(float)
    return data


def assert_monthly_series_is_contiguous(series_data: pd.DataFrame) -> None:
    if series_data.empty:
        return
    periods = pd.DatetimeIndex(series_data["period"].sort_values().unique())
    expected = pd.date_range(periods.min(), periods.max(), freq="MS")
    missing = expected.difference(periods)
    if len(missing):
        formatted = [value.strftime("%Y-%m") for value in missing[:12]]
        raise DataValidationError(
            "A série mensal possui lacunas e a política padrão não permite interpolação: "
            f"{formatted}"
        )
