# Camada de Wrappers — EcoFarm OS

Integração de dados heterogêneos (fazenda leiteira) com **layouts versionados** (`intraday:v1`, `monthly:v1`, `annual:v1`), **registry em YAML**, pipeline único e contrato principal `ProcessingResult`.

## Documentação

- **[docs/](docs/README.md)** — documentação técnica modular (arquitetura, layouts V1, exportação `;_;`, testes, produção, extensão, FAQ).
- Documento canônico do módulo no monorepo: [../docs/modules/wrappers-service.md](../docs/modules/wrappers-service.md).

## Dependências

```bash
pip install -r wrappers/requirements.txt
```

- **PyYAML** — layouts declarativos (`layout.yaml`).
- **pytest** — testes em `wrappers/testing/`.

## Estrutura do pacote

| Caminho | Função |
|---------|--------|
| `layouts/<família>/v1/layout.yaml` | Definição do layout (físico, schema, validação, mapeamento canônico). |
| `layouts/annual/v1/numeric_fields.yaml` | Lista de campos numéricos do anual (extensível). |
| `registry/file_registry.py` | Descobre e carrega todos os `layout.yaml`. |
| `core/pipeline.py` | **API principal:** `process_file(uri, layout_id, **options)`; secundária: `process_file_auto`. |
| `core/field_mapping.py` | Mapeamento de cabeçalhos compartilhado (pipeline + detector). |
| `processors/csv_processor.py` | Leitura CSV parametrizada. |
| `validators/` | `library.py` (regras) + `engine.py` (execução por `ref`). |
| `normalizers/` | Finalização por família; `harmonization.py` — passos YAML pós-normalização. |
| `mappers/engine.py` | Projeção canônica (`canonical_projection`). |
| `contracts.py` | `ProcessingResult`, `SourceContext`, descritores e relatório de validação. |
| `data_paths.py` | Resolução de nomes de CSV (`intraday_report.csv` vs legado). |
| `export/` | `ExportConfiguration`, `persist_processing_result`, serialização com separador `;_;`. |

## API pública

| Entrada | Uso |
|---------|-----|
| **`process_file(uri, layout_id)`** | Caminho oficial em produção (layout explícito). |
| `process_file_auto(uri)` | Conveniência com detecção de layout (emite `DeprecationWarning`). |
| `LayoutPipeline` | Casos avançados / testes internos. |

## Uso (layout explícito)

```python
from wrappers import process_file

r = process_file("data/intraday_report.csv", "intraday:v1")
print(r.processing_status, len(r.normalized_payload))
print(r.canonical_projection)
```

### Anual

O ano não vem no CSV; informe `year` ou use nome de arquivo com quatro dígitos (`relatorio_2022.csv`).

```python
process_file("data/annual_report.csv", "annual:v1", year=2022)
```

### Persistência pós-pipeline (opcional)

Após parsing, validação, normalização, harmonização e enriquecimento, pode gravar artefatos em disco (tabular com separador `;_;`, relatório de validação JSON e manifest com rastreabilidade):

```python
from pathlib import Path
from wrappers import ExportConfiguration, process_file

cfg = ExportConfiguration(base_dir=Path("data"))
r = process_file("data/intraday_report.csv", "intraday:v1", export_config=cfg)
```

Saída típica: `data/processed/<layout>/<versão>/[YYYY/MM/DD/]<stem>_normalized.delimited.csv`, `data/validation_reports/<run_id>_validation.json`, `<run_id>_manifest.json`. O diretório base é configurável via `ExportConfiguration.base_dir`.

## Novo layout (V2 ou nova família)

1. Crie `wrappers/layouts/<família>/v2/layout.yaml` (copie um V1 como base).
2. Ajuste `layout_id` (ex.: `intraday:v2`), `schema`, `validation_rules`, `canonical_mapping`.
3. Reinicie o processo (o registry faz `rglob("layout.yaml")` ao instanciar `LayoutRegistry`).
4. Adicione testes em `wrappers/testing/` com fixture CSV.

## Executar testes

```bash
# Na raiz do repositório (pacote exposto como wrappers via conftest)
pytest -q
```

Arquivos de dados esperados (ou nomes antigos): `intraday_report.csv` / `pesoXleite_parsed.csv`, `monthly_report.csv` / `validate_data_mensal.csv`, `annual_report.csv` / `validated_data_anual.csv`.
