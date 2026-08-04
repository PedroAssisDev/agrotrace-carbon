# Exportação pós-wrapper

## Função

Persistir artefactos depois de `process_file` quando se passa `export_config=ExportConfiguration(...)`. A função `persist_processing_result` em `export/output_writer.py` instancia `OutputWriter` e grava ficheiros.

## Configuração (`ExportConfiguration`)

- **`base_dir`** — raiz de todos os artefactos (obrigatório).  
- **`field_separator`** — por defeito `;_;` (string multi-caractere).  
- **`file_extension`** — por defeito `.delimited.csv` (deixa claro que não é CSV clássico).  
- **`encoding`** — UTF-8 por defeito.  
- Flags `write_normalized`, `write_canonical`, `write_rejected`, `write_validation_report`, `write_manifest`, `write_processing_log`, `write_empty_normalized_on_failure`.  
- **`use_date_subfolders`** — se `True`, subpastas `YYYY/MM/DD` sob `processed` e `rejected`.  
- Subpastas configuráveis: `input`, `processed`, `rejected`, `logs`, `validation_reports`.

## Organização de diretórios

Com `ensure_data_layout=True` (por defeito), criam-se:

- `base_dir/input/`  
- `base_dir/processed/`  
- `base_dir/rejected/`  
- `base_dir/logs/`  
- `base_dir/validation_reports/`

Ficheiros de dados processados e rejeitados também usam subpastas por família e versão extraídas de `layout_id` (ex.: `intraday/v1/`) e opcionalmente data.

## Ficheiros gerados (resumo)

| Tipo | Local típico | Conteúdo |
|------|----------------|----------|
| Normalizado | `processed/.../stem_normalized.delimited.csv` | Payload aceite serializado |
| Canónico | `processed/.../stem_canonical.delimited.csv` | Lista `canonical_projection.projections` |
| Rejeitados | `rejected/.../stem_rejected.delimited.csv` | Snapshots de linhas rejeitadas |
| Stub de falha | `rejected/.../stem_no_rows...` | Quando falha total sem rejeitados exportáveis |
| Relatório validação | `validation_reports/{run_id}_validation.json` | JSON do `ValidationReport` |
| Manifest | `validation_reports/{run_id}_manifest.json` | Rastreabilidade e paths |
| Log opcional | `logs/{run_id}_processing.json` | Resumo da execução |

`stem` inclui família, versão de catálogo, timestamp compacto UTC e status (ex.: `intraday_v1_20250325T120000Z_success`).

## Convenção de nomes e rastreabilidade

- **`run_id`** — UUID por execução de escrita.  
- Manifest liga: `source_uri`, `source_input_basename`, `source_checksum_sha256` (se calculado), `layout_id`, `catalog_display_name`, `field_separator`, contagens, `source_schema_version`, mapa `paths` com caminhos absolutos resolvidos.

## Por que não é CSV tradicional

O módulo `csv` da biblioteca padrão Python assume **delimitador de um único caractere**. O separador `;_;` tem **três** caracteres. A implementação em `export/delimited.py` (`DelimitedSerializer`):

- Junta campos com `;_;`.  
- Aspas estilo RFC 4180 quando o valor contém o separador, aspas, ou quebras de linha.  
- Serializa dict/list em JSON no texto da célula quando necessário.

## Como ler o ficheiro depois

Use `read_delimited_table` ou `read_delimited_file` de `wrappers.export.delimited_reader` com o **mesmo** `field_separator`. Os testes `test_delimited_roundtrip_*` e `test_read_delimited_roundtrip_with_writer` documentam o comportamento.

## Riscos e cuidados

- Consumidores que assumem vírgula ou `;` de um caractere vão **partir colunas**.  
- Ferramentas tipo Excel podem não abrir corretamente sem importação guiada com separador customizado.  
- Valores JSON em células exigem parser compatível na leitura.

## Exemplo de linhas exportadas

Cabeçalho:

```text
date;_;animal_id;_;milk;_;weight
```

Linha com valor que contém o separador (citado):

```text
2021-01-01;_;A1;_;10.5;_;500
```

## Governança

`validate_export_manifest` em `export/manifest.py` verifica chaves mínimas (`MANIFEST_REQUIRED_KEYS`). Testes garantem que um manifest gerado por `persist_processing_result` passa na validação.

Ver também: [production-usage](production-usage.md), [contracts](contracts.md), [troubleshooting](troubleshooting.md).
