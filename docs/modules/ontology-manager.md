# Módulo: ontology-manager

## Visão geral

Construir a ontologia de trabalho (AgroMRV-Lite), populá-la a partir dos dados
normalizados, validar e exportar (OWL/TTL).

**Posição:** etapas operacionais `ontology` e `semantic`.

## Responsabilidades

- Schema OWL + indivíduos a partir de DataFrame
- Validação semântica e export

## Não faz

- Não calcula emissões nem ancora

## Contratos (caminho Dash)

```python
from ontology import build_full_ontology, populate_from_dataframe, export_ontology, validate_all
```

Adapter: `frontend/services/ontology_adapter.py`.

`build_base_ontology` existe para uso mínimo; o orquestrador usa `build_full_ontology`.

## Entradas / saídas / persistência

- Entrada: dados normalizados
- Saída: exports em `$AGROTRACE_DATA_ROOT/ontology/` e `ontology_exports/`

## Limitações

- Classe `Lot` **não** modelada na OWL (RF005/RNF006 parciais)

## Testes

`pytest`; `validate_ontology_domain_source`, `validate_ontology_parameter_lifecycle`.

## Relacionados

- RF007 (RF004/RF005 parcial); RNF006
- README: `agrotrace-carbon-ontology-manager/README.md`
- [docs/ontology_agromrv_lite.md](../../agrotrace-carbon-ontology-manager/docs/ontology_agromrv_lite.md)
