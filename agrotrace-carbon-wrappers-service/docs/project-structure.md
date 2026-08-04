# Estrutura de diretórios e ficheiros

Raiz considerada: pasta do pacote **`wrappers/`** (contém `__init__.py`).

## Visão em árvore (conceitual)

```
wrappers/
├── __init__.py              # API pública reexportada
├── contracts.py             # Dataclasses e enums do domínio
├── provenance.py            # build_provenance
├── temporal.py              # parse_date, intervalos, descritores auxiliares
├── data_paths.py            # Nomes candidatos de CSV de exemplo
├── requirements.txt
├── README.md
├── docs/                    # Esta documentação
├── core/
│   ├── pipeline.py          # LayoutPipeline, process_file, process_file_auto
│   ├── field_mapping.py     # to_snake_case, map_schema_fields, scoring de detecção
│   ├── deprecation.py       # Avisos de API secundária
│   ├── inference.py         # infer_year_from_source_uri
│   └── row_snapshot.py      # logical_row_snapshot (rejeitados)
├── processors/
│   └── csv_processor.py     # read_csv_rows
├── registry/
│   ├── file_registry.py     # LayoutRegistry, default_registry
│   ├── layout_definition.py # LayoutDefinition
│   └── layout_detector.py   # detect_layout_id, LayoutDetectionError
├── layouts/
│   ├── intraday/v1/layout.yaml
│   ├── monthly/v1/layout.yaml
│   └── annual/v1/
│       ├── layout.yaml
│       └── numeric_fields.yaml
├── validators/
│   ├── engine.py            # ValidationEngine
│   └── library.py           # Funções de regra reutilizáveis
├── normalizers/
│   ├── engine.py            # NormalizationEngine, registo por família
│   ├── library.py           # finalize_* por família
│   └── harmonization.py     # apply_layout_harmonization, strip_whitespace_strings
├── mappers/
│   └── engine.py            # CanonicalMappingEngine
├── export/
│   ├── export_config.py     # ExportConfiguration
│   ├── output_writer.py     # OutputWriter, persist_processing_result, descritores
│   ├── delimited.py         # DelimitedSerializer (;_;), DelimitedExportStrategy (legado)
│   ├── delimited_reader.py  # Leitura compatível
│   └── manifest.py          # validate_export_manifest, MANIFEST_REQUIRED_KEYS
├── testing/
│   ├── conftest.py          # Alias do pacote wrappers para pytest
│   ├── test_pipeline.py
│   ├── test_export.py
│   ├── test_public_api.py
│   └── test_evolution.py
└── data/                    # Opcional: CSV grandes para testes de regressão
```

## Pasta por pasta

### Raiz

| Ficheiro | Papel |
|----------|--------|
| `contracts.py` | `ProcessingResult`, `ValidationReport`, descritores e contextos |
| `provenance.py` | Checksum opcional SHA-256, timestamp de leitura |
| `temporal.py` | Parsing de datas, intervalos mensais/anuais |
| `data_paths.py` | Tuplos de nomes de ficheiro para `resolve_csv` nos testes |

### `core/`

Orquestração do pipeline e utilitários de linha. **`pipeline.py`** é o coração: carrega layout, instancia motores, itera linhas, constrói resultado.

### `processors/`

Apenas leitura física CSV (`csv.DictReader`). Delimitador e encoding vêm do YAML (`physical`).

### `registry/`

- **`LayoutRegistry`**: `rglob("layout.yaml")` a partir de `layouts/`, indexa por `layout_id`.  
- **`LayoutDefinition`**: vista estável (id, família, versão, status, `catalog_display_name`).  
- **`layout_detector`**: lê a primeira linha não vazia e pontua layouts candidatos.

### `layouts/`

Cada layout versionado: `layouts/<layout_family>/v<versão_major>/layout.yaml`. O **`layout_id`** no YAML deve ser único (ex.: `monthly:v1`). Duplicados geram **aviso em log** e a última descoberta sobrescreve — evitar duplicar IDs.

### `validators/` e `normalizers/`

Motor + biblioteca de funções. Regras são compostas no YAML (`validation_rules`) com `ref` e parâmetros.  
Passos de harmonização declarativa do YAML (`harmonization.steps`) são aplicados em `normalizers/library.py`.

### `mappers/`

`CanonicalMappingEngine`: aplica lista `canonical_mapping.projections` do YAML.

### `export/`

Configuração, escrita de `processed/`, `rejected/`, `validation_reports/`, `logs/`, manifest JSON.

### `testing/`

Testes com `pytest`; adicionam o **diretório pai** de `wrappers` ao `sys.path` para `import wrappers`.

## Dependências entre módulos (resumo)

```
pipeline.py
  → registry, processors, validators, normalizers, mappers
  → contracts, provenance, temporal, row_snapshot
  → export (opcional via persist_processing_result)

export/output_writer.py → contracts, delimited.DelimitedSerializer (serialização e descritores inline)
```

## Core vs layout-específico

- **Core genérico:** pipeline, registry, serializers, contratos, deteção genérica.  
- **Layout-específico:** conteúdo de cada `layout.yaml` + funções em `validators/library.py` e `normalizers/library.py` referenciadas por `ref` ou por família (`intraday`, `monthly`, `annual`).  
- **Extensão:** novo layout pode reutilizar regras existentes ou exigir novas entradas no `ValidationEngine` / finalizadores (ver [extension-guide](extension-guide.md)).

---

Ver também: [core-components](core-components.md), [registry-and-versioning](registry-and-versioning.md).
