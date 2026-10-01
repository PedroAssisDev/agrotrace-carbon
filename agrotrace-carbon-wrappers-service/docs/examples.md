# Exemplos práticos

## Uso básico com layout explícito

```python
from wrappers import process_file

r = process_file("/data/file.csv", "monthly:v1")
print(r.layout_id, r.processing_status.value)
for row in r.normalized_payload[:3]:
    print(row.get("property_id"), row.get("period_start"))
```

## Com exportação

```python
from pathlib import Path
from wrappers import process_file, ExportConfiguration

cfg = ExportConfiguration(
    base_dir=Path("/data/ecofarm"),
    use_date_subfolders=True,
    write_processing_log=True,
)
r = process_file("/data/mensal.csv", "monthly:v1", export_config=cfg)
```

## Com ProcessingContext (ano anual)

```python
from wrappers import process_file, ProcessingContext

ctx = ProcessingContext(year=2023, encoding="utf-8", compute_checksum=True)
r = process_file("/data/anual.csv", "annual:v1", processing_context=ctx)
```

## Deteção automática

```python
from wrappers import detect_layout_id+process_file, LayoutDetectionError

try:
    r = detect_layout_id+process_file("/data/desconhecido.csv")
except LayoutDetectionError:
    # pedir layout humano ou mover para quarentena
    raise
```

## Falha de parsing

Ficheiro inexistente ou CSV ilegível: `processing_status` será `failure` e `quality_flags` inclui `parse_failure`.

## Rejeição parcial

Segunda linha com leite negativo no intradiário: `partial_success`, uma linha em `normalized_payload`, uma em `rejected_records` com `_reject_phase` igual a `validation`.

## Múltiplos layouts num job

```python
from wrappers import process_file

for lid, path in [("intraday:v1", "a.csv"), ("monthly:v1", "m.csv")]:
    r = process_file(path, lid)
    ...
```

## Ler exportação `;_;`

```python
from pathlib import Path
from wrappers.export import read_delimited_table

text = Path("/data/ecofarm/processed/.../stem_normalized.delimited.csv").read_text(encoding="utf-8")
cols, rows = read_delimited_table(text, field_separator=";_;")
```

Ver também: [production-usage](production-usage.md), [export](export.md).
