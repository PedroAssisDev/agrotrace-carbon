# Pendências

## P1 — Alta — RF008/RF009 — validate_emission_calculation_details
- **Problema:** falha na verificação `série por gás` (`len(timeseries.by_gas) >= 2`).
- **Evidência:** `_regressao.json` exit=1; duration ~127s.
- **Impacto:** enfraquece demonstração Cap. 5 de detalhes/explicabilidade por gás.
- **Arquivos:** `frontend/scripts/validate_emission_calculation_details.py`; `emission_detail_service.py`.
- **Correção:** garantir série multi-gás no payload de detalhe ou ajustar critério se domínio não produzir ≥2 gases no fixture.
- **Teste:** reexecutar `validate_emission_calculation_details.py --data-root <tmp>`.

## P2 — Alta — RF008 — validate_preliminary_calculation_form
- **Problema:** `RuntimeError` — parâmetros obrigatórios ausentes no `factor_catalog` da ontologia antes do cálculo.
- **Evidência:** stderr em `_regressao.json`.
- **Impacto:** formulário/caminho preliminar sem catálogo default não reproduz.
- **Arquivos:** `calculation_adapter.py` (`_resolve_factors`); `validate_preliminary_calculation_form.py`.
- **Correção:** seed de defaults pending no fixture do validador ou UI path.
- **Teste:** mesmo script isolado.

## P3 — Alta — RF005/RNF006 — Lot na OWL
- **Problema:** `OrganizationalGranularity.LOT` existe; classe `Lot` ausente em `ontology/schema.py`.
- **Impacto:** consistência semântica organizacional incompleta.
- **Correção:** adicionar classe Lot relacionada a Property; validar lot_id; relações Animal–Lot.
- **Teste:** extensão de `validate_temporal_model` + testes ontology.

## P4 — Média — Versionamento Git
- **Problema:** repositório sem commits; auditoria sem SHA.
- **Impacto:** irreprodutibilidade acadêmica da versão auditada.
- **Correção:** commit inicial (fora desta auditoria).

## P5 — Média — Sepolia
- **Problema:** ancoragem pública não reexecutada (proibido nesta auditoria).
- **Impacto:** Cap. 5 deve usar artefato histórico como documental ou nova execução controlada futura.
- **Correção:** roteiro Sepolia separado com inventário before/after.

## P6 — Média — Evidências visuais Cap. 5
- **Problema:** capturas UI não produzidas nesta rodada.
- **Impacto:** figuras do capítulo.
- **Correção:** seguir `08-plano-evidencias-capitulo-5.md`.

## P9 — Baixa — jsonschema só em optional-dev
- **Problema:** `jsonschema>=4.0` está em `[project.optional-dependencies] dev` do blockchain-service, não em deps de runtime.
- **Evidência:** inspeção estática ([Static audit 6.x blocks](a436cf5b-2f65-4876-9ce6-bd984bdf9a07)); nesta máquina os testes de schema passaram (venv com pacote instalado).
- **Impacto:** ambiente limpo sem `pip install -e ".[dev]"` pode não coletar `test_anchor_payload_schema.py`.
- **Correção:** promover a dependência de runtime ou documentar `[dev]` como obrigatório na regressão.
- **Teste:** venv limpa + coleta pytest do blockchain-service.

## P8 — Média — Integridade do inventário operacional (provenance.db)
- **Problema:** hash de `frontend/data/db/provenance.db` mudou durante a janela da auditoria (WAL/shm desapareceram).
- **Evidência:** baseline E8CB58F9… vs final 42BAFB2F…; `blockchain_service.db` intacto.
- **Impacto:** limita a afirmação de “zero alteração operacional”.
- **Correção:** auditar com bancos operacionais fechados (sem UI) e sem WAL aberto; preferir snapshot cópia read-only.
- **Teste:** inventário before/after com processo Dash parado.

## P7 — Baixa — Bypass data root
- **Problema:** `default_originals_dir` e `mock_data` paths fixos.
- **Impacto:** risco se alguém chamar storage sem `dest_dir`.
- **Correção:** falhar se data root custom e dest_dir omitido.
