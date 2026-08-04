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

## Etapas operacionais

1. Upload / entrada de dados.
2. Preservação do original (`save-file`) + hash SHA-256.
3. Registro inicial de proveniência.
4. Wrapper + lote normalizado.
5. População ontológica + validação semântica.
6. Cálculo preliminar (não publicado).
7. Revisão individual dos cálculos.
8. Aprovação geral do arquivo (decisão humana).
9. Publicação do manifesto final (`publication_service`).
10. Pacote de evidências + hashes + Merkle Root.
11. Ancoragem (provider `local_simulated` por padrão; provider EVM opcional).
12. Verificação de integridade.

## Pipeline: 11 operacional vs 18 visual

- **11 etapas** operacionais em `cycle_state.PIPELINE_STEP_DEFS` (execução real via
  `local_orchestrator`).
- **18 etapas** de apresentação em `pipeline_display.DISPLAY_PIPELINE_STEPS`, cada uma
  mapeada a um `orchestrator_step_id` (apenas visual).

Não altere a ordem do orquestrador para "alinhar" o stepper visual.

## Pausas do fluxo

- Pós-upload automático: para em `AWAITING_HUMAN_APPROVAL` (sem qualquer ação de blockchain).
- Pós-aprovação: publicação → evidência → âncora → verificação.

O gate obrigatório para qualquer ação de blockchain é `FINAL_ONTOLOGY_PUBLISHED`
(ver [ADR-003](decisions/ADR-003-approval-publication-and-blockchain-gate.md)). Correção e
recálculo geram nova versão preliminar — ver [result-state-model.md](result-state-model.md).
