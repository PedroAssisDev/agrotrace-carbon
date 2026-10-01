# AgroMRV-O Lite (Ontology Manager)

Ontologia de domínio para integração semântica de dados MRV leiteiros.

> Documento canônico do monorepo: [../docs/modules/ontology-manager.md](../docs/modules/ontology-manager.md)

## Install

```bash
pip install -e ".[dev]"
```

## Caminho usado pelo Dash (recomendado)

O orquestrador chama `build_full_ontology` (base + catálogos), não apenas
`build_base_ontology`:

```python
from ontology import (
    build_full_ontology,
    populate_from_dataframe,
    export_ontology,
    validate_all,
)
import pandas as pd

onto = build_full_ontology()
df = pd.read_csv("data.csv", sep=";_;", engine="python", dtype=str, keep_default_na=False)
populate_from_dataframe(onto, df, layout_name="annual_inventory")
validate_all(onto)
export_ontology(onto, "artifacts/ontology/agromrv_lite.owl", format="rdfxml")
```

Adapter: `frontend/services/ontology_adapter.py`.

## Quick start mínimo (base + catálogos manuais)

```python
from ontology import build_base_ontology, populate_catalogs, populate_from_dataframe, export_ontology
import pandas as pd

onto = build_base_ontology()
populate_catalogs(onto)
# ... populate / export ...
```

Ou: `python -m ontology.examples`

## Pipeline a partir de CSVs normalizados

```bash
python pipeline_run.py --data-dir ../data/processed --validate --export-ttl
```

## Testes

```bash
pytest
```

## Limitações

- Classe `Lot` não está modelada na OWL (parcial na auditoria de requisitos).

## Documentação

[docs/ontology_agromrv_lite.md](docs/ontology_agromrv_lite.md)
