# Aprovação e publicação

1. Cada cálculo obrigatório é revisado (`calculation_approval_service`).
2. Aprovação geral só com todos obrigatórios aprovados (`can_finalize`).
3. `finalize_file_approval` dispara `run_auto_pipeline_after_approval`.
4. `publication_service.publish_approved_cycle` gera manifesto tipado, hash canônico e arquivo em `frontend/data/publications/`.
5. Idempotência: mesmo conteúdo aprovado → mesmo hash/`publication_id`; conteúdo diferente com ciclo já publicado → erro.

Evento: `APPROVED_RESULT_PUBLISHED`.
