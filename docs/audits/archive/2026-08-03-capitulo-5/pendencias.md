# Pendências — Auditoria Capítulo 5

**Data:** 2026-08-03  
Prioridades: **crítica** · **alta** · **média** · **baixa** · **informativa**

Critérios de priorização: impacto no requisito acadêmico; risco de demonstração no Cap. 5; risco de funcionamento incorreto; risco a dados/credenciais.

---

## Críticas

Nenhuma pendência crítica que impeça a demonstração mínima do ciclo upload→aprovação→publicação→evidência→verificação no caminho simulado. O smoke e o full emission cycle passaram nesta sessão.

---

## Altas

### P-A01 — Ausência de API de recuperação do dado bruto (RF002)
- **Problema:** `save-file` persiste original + SHA-256, mas não expõe retrieve/load por ciclo ou hash.
- **Requisito:** RF002
- **Evidência:** inspeção de `save_file/__init__.py` (apenas `save_original_*`, `sha256_*`); adapter frontend só grava.
- **Impacto:** auditoria não demonstra recuperação bit-a-bit do bruto pela arquitetura.
- **Correção:** adicionar `retrieve_original(stored_path|sha256)` + teste round-trip; expor na aba Artefatos.
- **Arquivos:** `agrotrace-carbon-save-file/save_file/storage.py`; `frontend/services/save_file_adapter.py`
- **Validar:** unittest de round-trip; screenshot Cap. 5 de recuperação.

### P-A02 — Granularidade organizacional sem `Lot` e seed diário vazio (RF005, RNF006, RE-01)
- **Problema:** OWL modela Property/Animal; sem classe Lot. `validate_temporal_model` falhou com `FARM-DAILY-001` = 0 ciclos; reporting_period do seed só monthly.
- **Requisito:** RF005, RNF006, RE-01/CE1
- **Evidência:** ontology schema; saída do validate_temporal_model; inventário reporting_period.
- **Impacto:** CE1 não cobre plenamente granularidades da dissertação.
- **Correção:** (a) incluir Lot na ontologia **ou** revisar escopo na dissertação; (b) seed diário/anual representativo.
- **Arquivos:** `ontology/schema.py`; `frontend/scripts/seed_*`; dados emulated
- **Validar:** `validate_temporal_model.py` PASS; evidência OWL de Lot (se mantido).

### P-A03 — Parâmetros/fatores/GWP incompletos no resultado plano (RF009, RNF005)
- **Problema:** `ProvenanceMetadata` traz method_code/version; `to_flat_dict` não embute fatores/GWP; `validate_calculation_review` 1 FAIL (ANNUAL `factors_used`).
- **Requisito:** RF009, RNF005
- **Evidência:** log validate_calculation_review; código calculation_bundle.
- **Impacto:** explicabilidade incompleta “a partir do resultado”.
- **Correção:** serializar fatores/GWP/unidades no payload do resultado; corrigir caminho annual factors_used.
- **Arquivos:** `emissions/calculation_bundle.py`; `calculation_view_service.py`; factor mapping
- **Validar:** `validate_calculation_review.py` 0 FAIL; checklist RNF005 na UI.

### P-A04 — Divergência 8 rotas vs 12 telas / painel de auditoria colapsado (RF020, RNF002, RE-05)
- **Problema:** implementação tem 8 rotas (+ redirects); dissertação/rules citam 12; `TechnicalActionsPanel` colapsado falhou validação.
- **Requisito:** RF020, RNF002, RNF007, RE-05/CE5
- **Evidência:** `router.ROUTES`; validate_technical_audit 19 OK / 1 FAIL; HTTP 200 nas 8 rotas.
- **Impacto:** Cap. 5 precisa alinhar narrativa; 1 defeito UI na auditoria.
- **Correção:** atualizar texto Cap. 4/5 para consolidação 8 telas; corrigir estado inicial do painel.
- **Arquivos:** `frontend/components/audit/*`; docs dissertação; `validate_technical_audit.py`
- **Validar:** validate_technical_audit 20/20; screenshots CE5.

### P-A05 — Rastreabilidade cruzada proveniência↔ancoragem (RNF001, RE-04)
- **Problema:** após e2e, `audit_blockchain_anchor` na proveniência = 0; txs só no DB blockchain.
- **Requisito:** RNF001, RN-04 (separação ok), RE-04
- **Evidência:** inventário pós-e2e.
- **Impacto:** reconstrução “única” até tx exige dois stores.
- **Correção:** emitir link/evento de ancoragem na proveniência **sem** fundir papéis (manter RN-04).
- **Arquivos:** provenance adapter pós-anchor; `RegisterBlockchainAnchor` use case
- **Validar:** a partir de resultado publicado, UI mostra package_id + tx hash.

---

## Médias

### P-M01 — Correção/recálculo pouco demonstrado (RF010, RN-02)
- **Problema:** `request_correction` existe; `prov_core_prov_revision` historicamente 0; e2e cobriu rejeição, não o ramo completo correção→nova versão.
- **Requisito:** RF010, RN-02, RE-02
- **Correção:** script dedicado correção→recálculo com assert de nova versão preliminar.
- **Validar:** novo validate script PASS.

### P-M02 — Expectativas de seed desatualizadas
- **Problema:** `validate_pending_approval_seed` espera 17 pendências; ambiente tem centenas. `validate_property_filter` falha em rótulo “Embrapa P-1”. Jan–Jun 6≠7.
- **Requisito:** reprodutibilidade operacional (RNF009 parcial), CE5
- **Correção:** parametrizar expectativas ou reset controlado (com confirmação) antes de validar seed.
- **Validar:** scripts PASS em ambiente limpo+seed oficial.

### P-M03 — `jsonschema` ausente
- **Problema:** `test_anchor_payload_schema.py` não coleta.
- **Requisito:** RNF004/RNF011 complementar
- **Correção:** `pip install jsonschema` no extra `[dev]` do blockchain-service (após confirmação).
- **Validar:** pytest inclui o arquivo e passa.

### P-M04 — Versionamento de ABI / mapa de versões (RNF010)
- **Problema:** `contract_version: 1.0.0` no sepolia.json, mas ABI sem versionamento no filename; mapa unificado de versões do ciclo incompleto na UI.
- **Correção:** versionar path da ABI; exibir versões no manifesto/auditoria.
- **Validar:** checklist RNF010 na UI.

### P-M05 — Proteção de credenciais com repo sem Git (RNF012)
- **Problema:** `.env` com `BLOCKCHAIN_SEPOLIA_PRIVATE_KEY` SET; projeto sem `.git` → `.gitignore` não verificável.
- **Correção:** inicializar controle de versão (fora do escopo desta auditoria) e garantir ignore; sanitizar logs de scripts.
- **Validar:** ausência de segredos em artefatos gerados (grep sanitizado).

---

## Baixas

### P-B01 — Alias de gate `APPROVED_RESULT_PUBLISHED` / `FINAL_ONTOLOGY_PUBLISHED`
- **Problema:** dissertação usa o nome legado; frontend adotou alias canônico novo.
- **Impacto:** confusão narrativa, não funcional (ambos aceitos em `ELIGIBLE_ANCHOR_EVENT_TYPES`).
- **Correção:** glossário Cap. 5.
- **Prioridade:** baixa / informativa acadêmica.

### P-B02 — Fallback de canonicalização no frontend
- **Problema:** hash_helpers pode cair em compact JSON se import oficial falhar.
- **Correção:** falhar fechado em modo acadêmico quando canonical oficial indisponível.
- **Requisito:** RN-06 complementar.

### P-B03 — Teste negativo “forecast nunca entra na ontologia final”
- **Problema:** RN-03 atendido por arquitetura; falta assert dedicado.
- **Correção:** assert no full cycle.
- **Prioridade:** baixa.

---

## Informativas

### P-I01 — Repositório sem Git
- Identificação de versão da auditoria por inventário de arquivos, não por commit SHA.
- Limitação metodológica registrada no relatório completo.

### P-I02 — Dois bancos blockchain
- `frontend/data/db/blockchain_service.db` (caminho Dash) ≠ `agrotrace-carbon-blockchain-service/data/blockchain_service.db` (serviço/validador Sepolia).
- Cap. 5 deve citar qual DB/evidência está em uso.

### P-I03 — Anvil não configurado
- `BLOCKCHAIN_ANVIL_PRIVATE_KEY` / `CONTRACT_ADDRESS` EMPTY.
- Testes `blockchain_local` fora do escopo desta auditoria (decisão do usuário).

### P-I04 — Rules do Cursor ainda citam “12 telas”
- Dívida documental interna (`.cursor/rules`), não requisito acadêmico formal; alinhar com `router.py`.

### P-I05 — Artefato Sepolia histórico
- `interactive_validation_20260731_153031` SUCCESS usado como evidência CE4 **sem** nova tx nesta sessão (escopo acordado).

---

## Mapa rápido pendência → requisito

| Pendência | Requisitos |
|-----------|------------|
| P-A01 | RF002 |
| P-A02 | RF005, RNF006, RE-01 |
| P-A03 | RF009, RNF005 |
| P-A04 | RF020, RNF002, RNF007, RE-05 |
| P-A05 | RNF001, RE-04 |
| P-M01 | RF010, RN-02, RE-02 |
| P-M02 | operacional / CE5 |
| P-M03 | RNF004/RNF011 |
| P-M04 | RNF010 |
| P-M05 | RNF012 |
| P-B01 | RN-07 (narrativa) |
| P-B02 | RN-06 |
| P-B03 | RN-03 |
