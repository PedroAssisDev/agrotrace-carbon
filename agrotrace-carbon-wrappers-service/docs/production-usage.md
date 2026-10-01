# Uso em produção

Pressupõe Python 3.10+, dependência PyYAML instalada (`pip install -r requirements.txt`). O pacote `wrappers` deve ser importável (diretório pai no `PYTHONPATH` ou pacote instalado em modo editável).

## Processamento manual de um ficheiro

```python
from pathlib import Path
from wrappers import process_file, ExportConfiguration

src = Path("/dados/brutos/intraday.csv")
out = Path("/dados/ecofarm_out")
result = process_file(
    str(src),
    "intraday:v1",
    export_config=ExportConfiguration(base_dir=out),
    encoding="utf-8",
)
print(result.processing_status, len(result.normalized_payload), len(result.rejected_records))
```

## Pipeline automatizado (cron, Airflow, Prefect)

- Passo 1: depositar ficheiros num diretório de entrada.  
- Passo 2: para cada ficheiro, chamar `detect_layout_id+process_file` **ou** `detect_layout_id` + `process_file`.  
- Passo 3: inspecionar `processing_status`; se `failure`, alertar e mover ficheiro para quarentena.  
- Passo 4: agregar manifests em `validation_reports/` para painel de auditoria.

```python
from wrappers import detect_layout_id+process_file, ExportConfiguration, LayoutDetectionError
from pathlib import Path

def job(path: Path, base_out: Path):
    try:
        r = detect_layout_id+process_file(
            str(path),
            export_config=ExportConfiguration(base_dir=base_out),
        )
    except LayoutDetectionError as e:
        log.error("layout: %s", e.source_path)
        raise
    return r
```

## Processamento em lote

Iterar ficheiros com `pathlib.Path.glob`, acumular `ProcessingResult` ou serializar `to_dict()` para fila (Kafka, S3 + manifest). Para muito grande volume, considerar paralelização por processo (evitar partilhar o mesmo `run_id` de exportação sem coordenação).

## Reprocessamento de rejeitados

1. Ler ficheiros em `rejected/.../*_rejected*.delimited.csv` com `read_delimited_table` e o separador `;_;`.  
2. Corrigir dados na origem ou aplicar transformação controlada.  
3. Reenviar ao pipeline com o mesmo `layout_id`.

## Auditoria

- Comparar `source_schema_version` entre execuções para detectar mudança de catálogo.  
- Usar `provenance.checksum` quando `compute_checksum=True` na leitura.  
- Guardar `run_id` do manifest com tickets de suporte.

## Integração analítica e storage

- Carregar `normalized_payload` ou ficheiros exportados no armazém (Bronze/Silver).  
- Usar `canonical_projection` como camada já renomeada para modelos dimensionais intermediários.  
- JSON Lines de `ProcessingResult.to_dict()` por linha se o destino for lake orientado a eventos.

## Monitorização

- Métricas: contagem por `processing_status`, taxa de `rejected_record_count`, latência por ficheiro.  
- Alertas em `quality_flags` contendo `parse_failure` ou `all_records_rejected`.

## Rastreabilidade

Encadear: caminho do ficheiro de entrada, `run_id`, `layout_id`, `catalog_display_name`, paths no manifest.

## Troubleshooting em produção

Ver [troubleshooting](troubleshooting.md). Ativar logging Python no pacote `wrappers` para mensagens de registry e harmonização.

Ver também: [examples](examples.md), [export](export.md).
