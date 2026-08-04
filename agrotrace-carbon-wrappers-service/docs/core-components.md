# Componentes centrais

Referência ao código real. Caminhos relativos à pasta `wrappers/`.

## LayoutDefinition (`registry/layout_definition.py`)

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Vista imutável de metadados do layout sem expor o dict YAML completo. |
| **Campos** | `layout_id`, `layout_family`, `version`, `status`, `catalog_display_name` (opcional, ex.: `IntradayLayoutV1`). |
| **Entrada** | `LayoutDefinition.from_doc(doc)`. |
| **Dependências** | Nenhuma externa pesada. |

## LayoutRegistry (`registry/file_registry.py`)

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Descobrir e indexar todos os `layout.yaml` sob `layouts/`. |
| **Métodos principais** | `get(layout_id)`, `get_definition`, `layout_directory`, `list_layout_ids`, `list_definitions`, `source_schema_fingerprint`. |
| **Entradas** | Opcional `layouts_root`; por defeito `wrappers/layouts`. |
| **Comportamento** | `layout_id` duplicado: último ficheiro encontrado vence; regista-se `warning` no logger. |
| **Extensão** | Instanciar com outra raiz para testes ou pacotes empacotados diferente. |

## ValidationEngine (`validators/engine.py`)

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Executar lista `validation_rules` do YAML por registo lógico. |
| **Entrada** | `rules`, `row`, `line_index`, `report`. |
| **Saída** | `bool`: `False` se regra bloqueante falhar (ex.: obrigatórios, data inválida, negativos onde aplicável). |
| **Dependências** | `validators/library.py` via mapa interno `ref -> função`. |
| **Extensão** | Adicionar entrada em `_rule_registry()` e função na biblioteca. |

## NormalizationEngine (`normalizers/engine.py`)

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Finalizar registo após validação: tipos, intervalos, contextos `_temporal_context` e `_organizational_context`. |
| **Entrada** | `layout_doc`, `numeric_annual` (para anual), `row`, `line_index`, `report`, `options`. |
| **Saída** | `dict` normalizado ou `None` (rejeição na fase de normalização). |
| **Dispatch** | Mapa `_FAMILY_FINALIZERS` por `layout_family`; desconhecido usa finalizador genérico (remove chaves `_`). |
| **Extensão** | `NormalizationEngine.register_family_finalizer(family, fn)` ou novo ramo no mapa (código). |

## CanonicalMappingEngine (`mappers/engine.py`)

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Projetar campos lógicos para alvos canónicos declarados (`logical` → `target`). |
| **Métodos** | `project_record`, `project_batch` (inclui metadados `layout_family`, `layout_id` no dict de saída). |
| **Entrada** | Lista de registos **sem** prefixo `_` nas chaves usadas na projeção (o pipeline remove `_` só para o batch canónico). |
| **Limitação** | Não valida tipos nem unidades; apenas copia valores presentes. |

## OutputWriter (`export/output_writer.py`)

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Persistir artefactos pós-processamento: normalizado, canónico, rejeitados, relatório de validação, manifest, log opcional. |
| **Entrada** | `ExportConfiguration`, `ProcessingResult`. |
| **Saída** | Lista de descritores (`ProcessedFileDescriptor`, `RejectedFileDescriptor`). |
| **Função de módulo** | `persist_processing_result(result, config)` instancia `OutputWriter` e chama `write_all`. |

## DelimitedSerializer / DelimitedExportStrategy (`export/delimited.py`)

`DelimitedSerializer` é a implementação recomendada. `DelimitedExportStrategy` permanece como alias depreciado.

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Adaptador fino sobre `DelimitedSerializer` com separador configurável (por defeito `;_;`). |
| **Método** | `render(rows, columns=None)`. |

## ExportConfiguration (`export/export_config.py`)

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Configurar diretório base, separador, extensão (`.delimited.csv` por defeito), flags de escrita e subpastas. |
| **Campos relevantes** | `base_dir`, `field_separator` (default `;_;`), `processed_subdir`, `rejected_subdir`, `validation_reports_subdir`, `logs_subdir`, `use_date_subfolders`, `write_*` booleans. |

## ProcessingContext (`contracts.py`)

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Agrupar opções de execução sem colidir com `source_uri`. |
| **Campos** | `encoding`, `compute_checksum`, `year`, `extra`. |
| **Método** | `merged_options()` para fundir em `process_file`. |

## ProcessingResult (`contracts.py`)

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Resultado completo do pipeline (contrato principal). |
| **Campos principais** | `layout_id`, `layout_version`, `processing_status`, `source_context`, `normalized_payload`, `rejected_records`, `metadata`, `provenance`, `temporal_context`, `organizational_context`, `validation_report`, `quality_flags`, `source_schema_version`, `canonical_projection`. |
| **Método** | `to_dict()` para serialização genérica. |

## ValidationReport (`contracts.py`)

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Acumular erros, avisos, índices de linhas rejeitadas. |
| **Métodos** | `add_error`, `add_warning`, `to_dict()`. |

## ProvenanceMetadata (`contracts.py`)

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Identificar origem da leitura: URI, tipo, timestamp ISO, checksum opcional SHA-256. |

## TemporalDescriptor / OrganizationalDescriptor (`contracts.py`)

| Aspeto | Descrição |
|--------|-----------|
| **Finalidade** | Descrever granularidade temporal (instante, intervalo) e organizacional (propriedade, animal). |
| **Nota** | No payload normalizado, contextos também aparecem como dict em `_temporal_context` e `_organizational_context`. |

## Funções de entrada do pipeline (`core/pipeline.py`)

- **`process_file(source_uri, layout_id, *, registry=None, processing_context=None, export_config=None, **options)`** — ponto de entrada recomendado com layout explícito.  
- **`process_file_auto(source_uri, *, ...)`** — infere `layout_id`; pode levantar `LayoutDetectionError`.  
- **`LayoutPipeline`** — classe com `from_layout_id` e `process_file`.

---

Ver também: [contracts](contracts.md), [processing-flow](processing-flow.md), [export](export.md).
