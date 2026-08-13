# Guia da API pública

## Entrada principal

```python
from wrappers import process_file, ExportConfiguration

result = process_file("data/intraday_report.csv", "intraday:v1")
```

Parâmetros úteis: `processing_context`, `export_config`, `encoding`, `year` (anual), `compute_checksum`.

## Entradas secundárias

| API | Quando usar |
|-----|-------------|
| `detect_layout_id+process_file(uri)` | Prototipagem ou pipelines que inferem layout pelo cabeçalho. Prefira layout explícito em produção. |
| `LayoutPipeline.from_layout_id(...)` | Testes, extensão ou reutilização do orquestrador sem função facade. |
| `detect_layout_id(path)` | Apenas detecção, sem processar o ficheiro. |

## Metadados do resultado

- **`metadata["layout_family"]`** — família do layout (`intraday`, `monthly`, `annual`).
- **`metadata["wrapper_id"]`** — alias legado de `layout_family` (remoção futura).
- **`processing_status`** — status canónico; `metadata["status"]` repete o valor para compatibilidade.

## Exportação

```python
from pathlib import Path
from wrappers import ExportConfiguration, process_file

cfg = ExportConfiguration(base_dir=Path("data"))
process_file("in.csv", "intraday:v1", export_config=cfg)
```

Use `DelimitedSerializer` diretamente; `DelimitedExportStrategy` permanece apenas por compatibilidade.
