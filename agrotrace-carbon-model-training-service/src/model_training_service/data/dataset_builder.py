from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from model_training_service.domain.enums import Granularity


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-")
    return slug or "unknown-property"


class DatasetBuilder:
    """Materializa CSVs auditáveis.

    Consumidores de treinamento nesta versão:
    - regressão mensal → dataset mensal global (em memória / CSV global);
    - regressão anual → dataset anual global;
    - séries temporais → histórico mensal por propriedade.

    O dataset anual por propriedade é gravado apenas para auditoria; não há
    consumidor de treinamento (sem série temporal anual nem regressão por propriedade).
    """

    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)

    def materialize(self, data: pd.DataFrame) -> dict[str, str]:
        generated: dict[str, str] = {}
        self.output_dir.mkdir(parents=True, exist_ok=True)
        canonical_path = self.output_dir / "approved_results_canonical.csv"
        data.to_csv(canonical_path, index=False)
        generated["canonical"] = str(canonical_path)

        for granularity in Granularity:
            subset = data[data["granularity"].eq(granularity.value)].copy()
            if subset.empty:
                continue
            granularity_dir = self.output_dir / granularity.value
            global_dir = granularity_dir / "global"
            property_dir = granularity_dir / "properties"
            global_dir.mkdir(parents=True, exist_ok=True)
            property_dir.mkdir(parents=True, exist_ok=True)

            global_path = global_dir / f"{granularity.value}_global.csv"
            subset.to_csv(global_path, index=False)
            generated[f"{granularity.value}_global"] = str(global_path)

            for property_id, property_data in subset.groupby("property_id", sort=True):
                property_path = property_dir / f"{safe_slug(str(property_id))}.csv"
                property_data.to_csv(property_path, index=False)
                key = f"{granularity.value}:{property_id}"
                generated[key] = str(property_path)
                if granularity is Granularity.ANNUAL:
                    generated[f"audit_only:{key}"] = str(property_path)
        return generated
