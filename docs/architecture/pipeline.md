# Pipeline oficial

Fluxo único:

1. Upload / entrada
2. Preservação do original (`save-file`) + hash
3. Registro inicial de proveniência
4. Wrapper + lote normalizado
5. População ontológica + validação semântica
6. Cálculo preliminar (não publicado)
7. Revisão individual dos cálculos
8. Aprovação geral do arquivo
9. Publicação do manifesto final (`publication_service`)
10. Pacote de evidências + hashes + Merkle Root
11. Ancoragem simulada
12. Verificação de integridade

O orquestrador operacional tem **11 etapas** (`cycle_state.PIPELINE_STEP_DEFS`). O stepper visual tem **18 etapas** (`pipeline_display.DISPLAY_PIPELINE_STEPS`), cada uma mapeada a um `orchestrator_step_id`.

Pós-upload automático: para em `AWAITING_HUMAN_APPROVAL` (sem blockchain).
Pós-aprovação: publicação → evidência → âncora → verificação.
