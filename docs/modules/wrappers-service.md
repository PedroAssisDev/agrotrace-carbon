# Módulo: wrappers-service

## Visão geral

Normalizar arquivos brutos em lotes padronizados via layouts versionados.

**Posição:** etapas operacionais `wrapper` e `normalization`.

## Responsabilidades

- Aplicar layout e produzir lote normalizado
- Validar estrutura/consistência antes do cálculo

## Não faz

- Não calcula emissões nem popula ontologia

## Contratos

- `from wrappers import process_file`
- Adapter: `frontend/services/wrapper_adapter.py`
- Layouts: `intraday:v1`, `monthly:v1`, `annual:v1` em `layouts/`

Implementado em: `agrotrace-carbon-wrappers-service/core/pipeline.py`.

## Entradas / saídas / persistência

- Entrada: original + `layout_id`
- Saída: `ProcessingResult` (payload + projeção canônica)
- Persistência FE: `$AGROTRACE_DATA_ROOT/normalized/`

## Compatibilidade

`detect_layout_id + process_file` emite DeprecationWarning; permanece exportado.

## Testes

`pytest` no serviço (incluído na regressão).

## Relacionados

- RF003, RF004; RNF006, RNF008, RNF011
- README: `agrotrace-carbon-wrappers-service/README.md`
- Docs locais: `agrotrace-carbon-wrappers-service/docs/`
- [../domain/temporal-and-organizational-granularity.md](../domain/temporal-and-organizational-granularity.md)
