# Contratos de entrada e saída

## Contrato de entrada

### Parâmetros principais (`process_file`)

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `source_uri` | `str` | Caminho do ficheiro ou URI; o leitor actual remove prefixo `file://` e `lstrip("/")` para obter `Path`. |
| `layout_id` | `str` | Identificador de catálogo, ex.: `intraday:v1`. |
| `registry` | `LayoutRegistry \| None` | Registry customizado; `None` usa `default_registry()`. |
| `processing_context` | `ProcessingContext \| None` | Encoding, ano, checksum, `extra`. |
| `export_config` | `ExportConfiguration \| None` | Se definido, dispara persistência pós-pipeline. |
| `**options` | | `encoding`, `compute_checksum`, `year` (anual), repassados ao pipeline e a `SourceContext.extra` (exceto `source_uri`). |

### Formato físico

Definido no YAML: `physical.format`, `delimiter`, `encoding`, `header_row` (o código assume cabeçalho na primeira linha via `DictReader`).

## Contrato de processamento (estado interno)

Por linha, após mapeamento:

- Dicionário com **chaves lógicas** do schema (`date`, `property_id`, …).  
- Chaves internas possíveis: `_parsed_date` (`datetime.date`), mais tarde `_temporal_context`, `_organizational_context` em dict JSON-compatível.

## Contrato de saída: `ProcessingResult`

Campos relevantes (ver `contracts.py`):

- `layout_id`, `layout_version`  
- `processing_status`: `success` | `partial_success` | `failure`  
- `source_context`: `SourceContext` com `source_uri`, `media_type`, `extra`  
- `normalized_payload`: lista de dicts **com** campos internos `_temporal_context`, `_organizational_context` quando aplicável  
- `rejected_records`: snapshots sem chaves `_`, mais `_line_index`, `_reject_phase`  
- `metadata`: dict com `layout_family`, `layout_id`, `catalog_display_name`, contagens, `processing_timestamp`, `status` (`wrapper_id` mantido por compatibilidade)  
- `provenance`: `ProvenanceMetadata`  
- `temporal_context`, `organizational_context`: descritores de **nível de lote** derivados de `granularity` no YAML (não substituem os dicts por linha)  
- `validation_report`: erros, avisos, `rejected_indices`  
- `quality_flags`: lista de strings  
- `source_schema_version`: fingerprint tipo `sha256:…` ou fallback  
- `canonical_projection`: dict com chave `projections` (lista de dicts) e opcionalmente `layout_family`, `layout_id`

## Pseudo-JSON: `ProcessingResult.to_dict()` (exemplo truncado)

```json
{
  "layout_id": "intraday:v1",
  "layout_version": "1.0",
  "processing_status": "success",
  "source_context": {
    "source_uri": "/data/in.csv",
    "media_type": "text/csv",
    "extra": { "encoding": "utf-8", "compute_checksum": false }
  },
  "normalized_payload": [
    {
      "date": "2021-01-01",
      "animal_id": "A1",
      "milk": 10.5,
      "weight": 500.0,
      "_temporal_context": { "type": "instant", "value": "2021-01-01", "granularity": "day" },
      "_organizational_context": { "granularity": "animal", "identifier": "A1" }
    }
  ],
  "rejected_records": [],
  "metadata": {
    "wrapper_id": "intraday",
    "layout_id": "intraday:v1",
    "catalog_display_name": "IntradayLayoutV1",
    "processing_timestamp": "2025-03-25T12:00:00Z",
    "record_count": 1,
    "rejected_record_count": 0,
    "status": "success"
  },
  "provenance": {
    "source_uri": "/data/in.csv",
    "source_type": "csv",
    "read_timestamp": "2025-03-25T11:59:59Z"
  },
  "validation_report": { "rejected_count": 0, "errors": [], "warnings": [], "rejected_indices": [] },
  "quality_flags": [],
  "source_schema_version": "sha256:abcd0123efgh4567",
  "canonical_projection": {
    "projections": [ { "MilkProductionObservation.observedAt": "2021-01-01", "Animal.identifier": "A1" } ],
    "layout_family": "intraday",
    "layout_id": "intraday:v1"
  }
}
```

## Significado dos campos transversais

- **metadata** — agregados operacionais e ligação ao catálogo (`catalog_display_name`).  
- **provenance** — origem e momento da leitura; checksum opcional para auditoria de ficheiro bruto.  
- **temporal_context / organizational_context (nível lote)** — resumo da granularidade declarada no YAML; útil quando todas as linhas partilham o mesmo enquadramento.  
- **validation_report** — detalhe para debugging e para exportação JSON em `validation_reports/`.  
- **quality_flags** — sinalização grossa para monitorização (ex.: avisos de validação).  
- **processing_status** — sumário para orquestração (sucesso, parcial, falha).  
- **source_schema_version** — correlacionar resultado com versão exata do layout YAML usado.

---

Ver também: [export](export.md) para o manifest em disco, [core-components](core-components.md).
