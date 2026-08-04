# Modelo de estados do resultado

Estados de um resultado de cálculo ao longo do ciclo. Fonte de vocabulário no frontend:
`frontend/services/domain_catalog.py` (+ `cycle_state` / `pipeline_display` para etapas).

## Estados

```text
preliminar (preliminary)
  → em revisão (under review)
  → aprovado (approved)  |  rejeitado (rejected)
  → publicado (published)
```

- **preliminar:** resultado calculado, ainda não publicado; só proveniência.
- **em revisão:** cálculos sob avaliação individual.
- **aprovado / rejeitado:** decisão humana sobre o conjunto.
- **publicado:** manifesto final publicado (habilita evidências e ancoragem).

Correção e recálculo **não** alteram um resultado publicado no lugar: geram uma **nova
versão preliminar**, que percorre novamente revisão → aprovação → publicação.

## Eventos canônicos (emissão única por fato)

- `RAW_DATA_UPLOADED`, `WRAPPER_EXECUTED`, `NORMALIZED_BATCH_CREATED`
- `SEMANTIC_MAPPING_COMPLETED`, `SEMANTIC_VALIDATION_COMPLETED`
- `CALCULATION_PRELIMINARY_RESULT_CREATED`
- `CALCULATION_APPROVED` / `CALCULATION_REJECTED` / `CYCLE_APPROVED`
- `APPROVED_RESULT_PUBLISHED` (alias de leitura: `FINAL_ONTOLOGY_PUBLISHED`)
- `EVIDENCE_PACKAGE_CREATED`, `BLOCKCHAIN_ANCHORED`, `INTEGRITY_VERIFIED`
- `PIPELINE_STEP_FAILED`

Aliases legados são aceitos **apenas na leitura** e não devem ser reemitidos.

O gate `FINAL_ONTOLOGY_PUBLISHED` é obrigatório para qualquer ação de blockchain
(ver [ADR-003](decisions/ADR-003-approval-publication-and-blockchain-gate.md)).
