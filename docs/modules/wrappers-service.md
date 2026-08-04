# Módulo: wrappers-service

## Finalidade

Normalizar arquivos brutos em lotes padronizados, por meio de layouts versionados.

## Responsabilidades

- Selecionar/aplicar o layout adequado e produzir um lote normalizado.
- Validar estrutura/consistência antes do cálculo.

## Não faz

- Não calcula emissões nem popula a ontologia.

## Contratos com o frontend

- `from wrappers import process_file`.
- Adapter: `frontend/services/wrappers_adapter` (fallback de import tolerado).

## Layouts

Versionados no pacote (ex.: `intraday:v1`, `monthly:v1`, `annual:v1`). Detalhe em
`agrotrace-carbon-wrappers-service/docs/layouts/`.

## Entradas / saídas / persistência

- Entrada: original + layout.
- Saída: lote normalizado em `AGROTRACE_DATA_ROOT/normalized/`.

## Compatibilidade legada

`process_file_auto` está *deprecated*, mas permanece exportado no caminho de fallback —
remover somente de forma coordenada com os adapters.

## Testes e comandos

- `pytest` no diretório do serviço (incluído na regressão).

## Relacionados

- RF003, RF004; RNF006, RNF008, RNF011.
- Detalhe: `agrotrace-carbon-wrappers-service/README.md` e `docs/`.
- Granularidades: [../domain/temporal-and-organizational-granularity.md](../domain/temporal-and-organizational-granularity.md).
