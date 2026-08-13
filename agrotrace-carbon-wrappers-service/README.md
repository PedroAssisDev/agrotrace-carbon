# Camada de Wrappers — EcoFarm OS

Integração de dados heterogêneos (fazenda leiteira) com **layouts versionados**
(`intraday:v1`, `monthly:v1`, `annual:v1`), registry em YAML, pipeline único e contrato
`ProcessingResult`.

> Documento canônico do monorepo: [../docs/modules/wrappers-service.md](../docs/modules/wrappers-service.md)

## Documentação técnica local

- **[docs/](docs/README.md)** — arquitetura, layouts V1, exportação, testes, FAQ.

## Dependências

Na raiz deste serviço:

```bash
pip install -r requirements.txt
# ou: pip install -e ".[dev]"
```

- **PyYAML** — layouts declarativos (`layout.yaml`)
- **pytest** — testes em `testing/`

## Estrutura do pacote

O pacote é exposto como `wrappers` (`pyproject.toml` `package-dir`). Caminhos relativos
à raiz do serviço:

| Caminho | Função |
|---------|--------|
| `layouts/<família>/v1/layout.yaml` | Definição do layout |
| `layouts/annual/v1/numeric_fields.yaml` | Campos numéricos do anual |
| `registry/file_registry.py` | Carrega todos os `layout.yaml` |
| `core/pipeline.py` | API: `process_file(uri, layout_id, **options)` |
| `processors/csv_processor.py` | Leitura CSV |
| `validators/` | Regras + engine |
| `normalizers/` | Finalização por família |
| `mappers/engine.py` | Projeção canônica |
| `contracts.py` | `ProcessingResult`, etc. |
| `export/` | Persistência opcional pós-pipeline |
| `testing/` | Testes e fixtures |

## API pública

| Entrada | Uso |
|---------|-----|
| **`process_file(uri, layout_id)`** | Caminho oficial (layout explícito) |
| `detect_layout_id` + `process_file(uri)` | Conveniência (DeprecationWarning) |

```python
from wrappers import process_file

r = process_file("data/intraday_report.csv", "intraday:v1")
print(r.processing_status, len(r.normalized_payload))
```

Anual (ano não vem no CSV):

```python
process_file("data/annual_report.csv", "annual:v1", year=2022)
```

## Integração Dash

`frontend/services/wrapper_adapter.py` → `process_file`. Lotes normalizados gravados sob
`$AGROTRACE_DATA_ROOT/normalized/`.

## Novo layout

1. Crie `layouts/<família>/v2/layout.yaml`
2. Ajuste `layout_id`, schema, validação, mapeamento
3. Adicione testes em `testing/`

## Testes

```bash
pytest -q
```
