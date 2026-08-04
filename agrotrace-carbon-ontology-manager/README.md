# AgroMRV-O Lite (Ontology Manager)

Lightweight, self-contained domain ontology for semantic integration of dairy MRV data.

> Documento canônico do módulo: [../docs/modules/ontology-manager.md](../docs/modules/ontology-manager.md).

## Install

```bash
pip install -e ".[dev]"
```

## Quick start

```python
from ontology import build_base_ontology, populate_catalogs, populate_from_dataframe, export_ontology
import pandas as pd

onto = build_base_ontology()
populate_catalogs(onto)

df = pd.read_csv("data.csv", sep=";_;", engine="python", dtype=str, keep_default_na=False)
populate_from_dataframe(onto, df, layout_name="annual_inventory")

export_ontology(onto, "artifacts/ontology/agromrv_lite.owl", format="rdfxml")
export_ontology(onto, "artifacts/ontology/agromrv_lite.ttl", format="turtle")
```

Or run the end-to-end example:

```bash
python -m ontology.examples
```

## Pipeline (processed data)

Build and populate the ontology from normalized CSVs exported by the wrappers service:

```bash
python pipeline_run.py --data-dir ../data/processed
```

The script auto-discovers the latest `*_normalized.delimited.csv` for annual, intraday, and monthly data. Override individual inputs with `--annual-csv`, `--intraday-csv`, or `--monthly-csv`. Use `--validate` to run ontology checks before export, and `--export-ttl` to also write a Turtle file.

## Tests

```bash
pytest
```

## Documentation

See [docs/ontology_agromrv_lite.md](docs/ontology_agromrv_lite.md).
