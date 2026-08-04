# Fluxo de processamento

Alinhado a `core/pipeline.py` (`LayoutPipeline.process_file`).

## Sequência end-to-end

1. **Entrada bruta** — ficheiro CSV em `source_uri` (caminho ou `file://`).
2. **Layout** — `process_file` exige `layout_id`; `process_file_auto` usa `detect_layout_id` na primeira linha não vazia.
3. **Catálogo** — `LayoutRegistry.get(layout_id)` e pasta do layout para ficheiros auxiliares.
4. **Parsing físico** — `read_csv_rows` com `delimiter` e `encoding` do YAML (encoding pode ser sobrescrito).
5. **Proveniência** — `build_provenance` com timestamp; checksum opcional.
6. **Por linha** — linhas vazias são ignoradas.
7. **Mapeamento lógico** — aliases ou modo `snake_case_headers`.
8. **Datas** — `_inject_parsed_dates` trata o primeiro campo `type: date` do schema; define `_parsed_date` e ISO na chave lógica.
9. **Validação** — `ValidationEngine.apply` com regras do YAML.
10. **Rejeição (validação)** — snapshot lógico com `_line_index` e `_reject_phase: validation`.
11. **Normalização** — `NormalizationEngine.finalize_record`; falha gera `_reject_phase: normalization`.
12. **Harmonização** — `apply_layout_harmonization` no normalizer (sem efeito se não houver configuração).
13. **Payload** — registo harmonizado é acrescentado à lista.
14. **Status** — `SUCCESS`, `PARTIAL_SUCCESS` ou `FAILURE`; `quality_flags` descreve causas.
15. **Projeção canónica** — cópia dos registos sem chaves que começam por `_` para `project_batch`.
16. **Resultado** — `ProcessingResult`; exportação opcional com `export_config`.

## Ordem harmonização versus canónico

Harmonização ocorre depois da normalização e antes da projeção canónica em lote.

## Falha de parsing

Exceção na leitura: `FAILURE`, `STRUCTURAL_PARSE_ERROR`, `parse_failure` nas flags.

## Rejeição parcial

Algumas linhas aceites e outras rejeitadas: `PARTIAL_SUCCESS` e `rejected_records` com fase.

Ver também: [validation](validation.md), [normalization](normalization.md), [harmonization](harmonization.md), [canonical-mapping](canonical-mapping.md).
