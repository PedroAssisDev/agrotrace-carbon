# Documentação dos testes

Local: `wrappers/testing/`. Framework: **pytest**. Os ficheiros adicionam o diretório **pai** da pasta `wrappers` a `sys.path` para permitir `import wrappers` sem instalação como pacote.

Execução recomendada:

```bash
cd "<diretório pai de wrappers>"
python -m pytest wrappers/testing -q
```

## Visão por ficheiro

### `test_pipeline.py` — registry + pipeline + integração de export

| Teste | O que testa | Por que existe | Comportamento protegido | Risco evitado | Arquitetura | Entrada | Esperado | Falha |
|-------|-------------|----------------|-------------------------|---------------|-------------|---------|----------|--------|
| `test_registry_lists_v1_layouts` | `default_registry().list_layout_ids()` contém os três V1 | Garantir catálogo mínimo | Registry descobre YAMLs | Deploy sem layouts | Registry | Nenhuma | três IDs presentes | Layouts ausentes ou path errado |
| `test_layout_definition_from_registry` | `get_definition("intraday:v1")` | Metadados estáveis | `LayoutDefinition` e `catalog_display_name` | Regressão de campos | Registry | Nenhuma | família intraday, versão 1.0, nome IntradayLayoutV1 | YAML sem `catalog_display_name` |
| `test_all_v1_catalog_display_names` | Nomes para os três layouts | Consistência V1 | Três rótulos humanos | Erro de documentação ou YAML | Registry | Nenhuma | três nomes esperados | Falta de chave em algum YAML |
| `test_registry_list_layout_definitions` | `list_definitions` | API de catálogo para UIs | Conjunto de `LayoutDefinition` | Lista vazia | Registry | Nenhuma | superset dos três IDs | Registry vazio |
| `test_process_file_with_export_config` | `process_file` + export | Integração pipeline e disco | Manifest e `catalog_display_name` no JSON | Export quebrada | Pipeline + Export | CSV intradiário mínimo em tmp | SUCCESS, manifest com nome | Permissões ou mudança de paths |
| `test_processing_context_merges_year` | `ProcessingContext(year=2022)` | Ano explícito para anual | `year` no payload | Ano errado em jobs | Pipeline + Contracts | CSV anual mínimo | year 2022 | Context não fundido |
| `test_partial_success_collects_rejected_records` | Linha válida + inválida | Rejeição parcial | Status partial, fase validation | Perda de rejeitados | Validation | CSV duas linhas | 1 aceite, 1 rejeitada | Mudança de ordem de regras |
| `test_intraday_v1` | CSV real intradiário | Regressão de volume | Muitas linhas, animal_id, projeção | Quebra de layout real | Pipeline | `data/` opcional | SUCCESS, len grande | Skip se sem data |
| `test_monthly_v1` | CSV real mensal | Regressão mensal | property_id, period_end | Quebra mensal | Pipeline | `data/` opcional | SUCCESS | Skip se sem data |
| `test_annual_v1` | CSV real anual | Regressão anual | year, property_name | Quebra anual | Pipeline | `data/` opcional | SUCCESS | Skip se sem data |
| `test_monthly_layout_harmonization_strip_property_id` | harmonização declarativa no YAML mensal | Garantir trim pós-normalização | `property_id` sem espaços externos | Regressão semântica | Pipeline + Normalizers | CSV mensal mínimo em tmp | SUCCESS + campo trimado | Passos YAML ignorados |

Fixture `data_dir`: exige pasta `wrappers/data`; senão skip dos testes que dependem de CSV grandes.

### `test_export.py` — delimitador e escritor

| Teste | O que testa | Protege | Entrada | Esperado | Falha |
|-------|-------------|---------|---------|----------|--------|
| `test_delimited_roundtrip_multichar_separator` | `DelimitedSerializer` com `;_;` | Aspas quando valor contém separador | dicts de exemplo | linhas com quoting correcto | Regressão em escape |
| `test_persist_writes_manifest_and_normalized` | `persist_processing_result` | Manifest + path normalizado | `ProcessingResult` sintético | field_separator, family, output_normalized | OutputWriter quebrado |
| `test_export_writes_rejected_sidecar` | Ficheiro rejeitado | Fluxo partial com rejected | Resultado com `rejected_records` | ficheiro rejected e manifest | Pastas ou glob |
| `test_ensure_data_layout_creates_input_and_logs` | `write_processing_log` | Árvore base e logs | Resultado vazio mensal | dirs input/logs e JSON | Flags de config |

### `test_evolution.py` — leitura, deteção, auto e manifest

| Teste | O que testa | Protege | Entrada | Esperado | Falha |
|-------|-------------|---------|---------|----------|--------|
| `test_read_delimited_roundtrip_with_writer` | Leitor + escritor | Round-trip com lista JSON | texto gerado | colunas e nested | Parser delimited |
| `test_detect_layout_intraday` | Deteção intradiário | Cabeçalho Date,Tag,... | tmp CSV | intraday:v1 | Prioridade ou schema |
| `test_detect_layout_monthly` | Deteção mensal | Cabeçalho Property;Period;... | tmp CSV | monthly:v1 | Delimitador |
| `test_detect_layout_annual_min_columns` | Deteção anual | min_column_count | cabeçalho largo | annual:v1 | Threshold |
| `test_detect_layout_id+process_file_intraday` | `detect_layout_id+process_file` | Pipeline sem layout explícito | tmp CSV | payload 1 linha | Deteção falhou |
| `test_detect_layout_raises_ambiguous` | Cabeçalho inválido | Sem match | uma coluna | None | Falso positivo |
| `test_detect_layout_id+process_file_raises_layout_detection_error` | Erro explícito | Operador sabe falhar | uma coluna | excepção com source_path | API silenciosa |
| `test_validate_export_manifest_ok_minimal` | Governança mínima | Chaves obrigatórias | dict mínimo | sem erros | MANIFEST_REQUIRED_KEYS |
| `test_validate_export_manifest_missing_keys` | Falha governança | dict incompleto | erros | validação útil | Falso negativo |
| `test_persist_manifest_passes_governance` | Manifest real | Fim-a-fim escrita + validate | persist + load | lista vazia de erros | Divergência de campos |

## Tipos de teste (classificação)

- **Unitários:** serializers, harmonização declarativa, validação de manifest.  
- **Integração:** `process_file` com tmp, export e `detect_layout_id+process_file`.  
- **Regressão / dados reais:** três testes V1 com `data/` (condicionais).  
- **Compatibilidade:** round-trip `;_;`, deteção entre layouts.

### `test_validation_refs.py` — uma função por `ref` de validação

| Teste | Ref coberta |
|-------|-------------|
| `test_validation_refs_frozen_set_matches_engine` | Sincroniza `COVERED_VALIDATION_REFS` com `validation_rule_refs()` |
| `test_ref_required_fields_fails` | `required_fields` |
| `test_ref_date_valid_fails` | `date_valid` |
| `test_ref_non_negative_fails` | `non_negative` |
| `test_ref_first_day_of_month_warning` | `first_day_of_month` |
| `test_ref_lactating_consistency_warning` | `lactating_consistency` |
| `test_ref_dry_consistency_warning` | `dry_consistency` |
| `test_ref_milk_sales_le_production_warning` | `milk_sales_le_production` |
| `test_ref_weight_range_warning` | `weight_range_warning` |
| `test_ref_annual_numeric_non_negative_fails` | `annual_numeric_non_negative` |
| `test_unknown_ref_logs_but_does_not_crash` | refs desconhecidas (warning) |

### `test_registry_duplicates.py`

`test_duplicate_layout_id_last_wins_and_logs_warning` — dois `layout.yaml` com o mesmo `layout_id` sob uma raiz temporária; espera aviso de log com «duplicado» e registo indexado.

### `test_harmonization_steps.py`

Cobre `strip_whitespace_strings` e `apply_layout_harmonization` com o documento real `monthly:v1`.

## Lacunas conhecidas

- Testes de carga e de permissões em sistemas de ficheiros remotos.  
- Contract testing HTTP se surgir API de ingestão.

Ver também: [troubleshooting](troubleshooting.md), [extension-guide](extension-guide.md).
