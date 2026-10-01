# Ciclo de vida do dado

Fluxo único do dado bruto até a verificação. Antes da aprovação e publicação final, os
resultados são **preliminares**; apenas proveniência é registrada. A ancoragem ocorre
somente após a publicação final.

```text
entrada
  → preservação do original (save-file + SHA-256)
  → [proveniência contínua registra cada etapa]
  → wrapper (lote normalizado)
  → normalização / mapeamento semântico
  → validação semântica
  → ontologia de trabalho
  → cálculo preliminar (não publicado)
  → revisão individual dos cálculos
  → aprovação geral (humana)
  → publicação final (manifesto)
  → pacote de evidências
  → hashes + Merkle Root
  → ancoragem (simulada por padrão | EVM)
  → verificação de integridade
```

## Etapas operacionais (11) — orquestrador

Fonte: `frontend/services/cycle_state.py` (`PIPELINE_STEP_DEFS`), executadas por
`frontend/services/local_orchestrator.py`.

| # | `step_id` | Função do orquestrador | Serviço dominante |
|---|-----------|------------------------|-------------------|
| 1 | `raw_data` | `register_raw_upload` | frontend + save-file + proveniência |
| 2 | `wrapper` | `run_wrapper_step` | wrappers-service |
| 3 | `normalization` | `run_wrapper_step` | wrappers-service |
| 4 | `ontology` | `run_ontology_step` | ontology-manager |
| 5 | `semantic` | `run_semantic_step` | ontology-manager |
| 6 | `calculation` | `run_calculation_step` | calculation-service |
| 7 | `approval` | `run_approval_step` | frontend + proveniência |
| 8 | `publication` | `run_publication_step` | `publication_service` + proveniência |
| 9 | `evidence` | `run_evidence_step` | blockchain-service |
| 10 | `blockchain` | `run_anchoring_step` | blockchain-service |
| 11 | `verification` | `run_verification_step` | blockchain-service + proveniência |

## Vocabulário de etapas: 11 / 18 / 19 / 20

| Camada | Contagem | Onde | Papel |
|--------|----------|------|-------|
| Orquestrador | **11** | `cycle_state.PIPELINE_STEP_DEFS` | Execução real |
| Stepper visual | **18** | `pipeline_display.DISPLAY_PIPELINE_STEPS` | Apresentação (mapeia para `orchestrator_step_id`) |
| Timeline de auditoria | **19** | `pipeline_display.AUDIT_STEP` | Só na timeline de proveniência (`PROVENANCE_CHAIN_VERIFIED`) |
| Eventos canônicos | **1–20** | modelo conceitual / ledger | Vocabulário de eventos; não são 20 funções do orquestrador |

No stepper visual, a divisória pós-etapa 13 marca o gate blockchain
(`FINAL_ONTOLOGY_PUBLISHED`). Etapas visuais 14–18 correspondem às etapas
operacionais 9–11.

Não altere a ordem do orquestrador para "alinhar" o stepper visual.

## Pausas do fluxo

- Pós-upload automático (`run_auto_pipeline_after_ingestion`): para em
  `AWAITING_HUMAN_APPROVAL` (sem qualquer ação de blockchain).
- Pós-aprovação (`run_auto_pipeline_after_approval`): publicação → evidência →
  âncora → verificação.

O gate obrigatório para qualquer ação de blockchain é `FINAL_ONTOLOGY_PUBLISHED`
(ver [ADR-003](decisions/ADR-003-approval-publication-and-blockchain-gate.md)). Correção e
recálculo geram nova versão preliminar — ver [result-state-model.md](result-state-model.md).

## Aprovação e publicação (resumo)

1. Cada cálculo obrigatório é revisado (`calculation_approval_service`).
2. Aprovação geral só com todos obrigatórios aprovados (`can_finalize`).
3. `finalize_file_approval` dispara `run_auto_pipeline_after_approval`.
4. `publication_service.publish_approved_cycle` gera manifesto tipado, hash canônico e
   arquivo sob `$AGROTRACE_DATA_ROOT/publications/`.
5. Idempotência: mesmo conteúdo aprovado → mesmo hash/`publication_id`.

Implementado em: `frontend/services/publication_service.py`,
`frontend/services/calculation_approval_service.py`.
