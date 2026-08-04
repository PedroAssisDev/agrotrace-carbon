# Módulo: ontology-manager

## Finalidade

Construir a ontologia de trabalho (AgroMRV-Lite), populá-la a partir dos dados
normalizados, validar e exportar (OWL/TTL). Base para a ontologia final publicada.

## Responsabilidades

- Montar o schema OWL e popular indivíduos a partir de um DataFrame.
- Validar consistência semântica; exportar a ontologia.

## Não faz

- Não calcula emissões nem ancora artefatos.

## Contratos com o frontend

- `from ontology import build_full_ontology, populate_from_dataframe, export_ontology`
  e `validate_all`.
- Adapter: `frontend/services/ontology_adapter`.

## Entradas / saídas / persistência

- Entrada: dados normalizados.
- Saída: ontologia de trabalho/final; exports em `AGROTRACE_DATA_ROOT/ontology_exports/`
  (**gerado**, regenerável).

## Limitações conhecidas

- A classe `Lot` **não** está modelada na OWL (RF005/RNF006 parciais na auditoria). Não é
  tratada como resolvida.

## Testes e comandos

- `pytest` no serviço; `validate_ontology_domain_source`, `validate_ontology_parameter_lifecycle`.

## Relacionados

- RF007 (e RF004/RF005 parcial); RNF006.
- Detalhe: `agrotrace-carbon-ontology-manager/README.md`, `docs/ontology_agromrv_lite.md`.
- Publicação final: [../architecture/result-state-model.md](../architecture/result-state-model.md).
