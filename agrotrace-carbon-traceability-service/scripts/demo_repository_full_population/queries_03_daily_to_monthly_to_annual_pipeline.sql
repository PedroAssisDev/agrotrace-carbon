-- ============================================================
-- CASO 3: FAZENDA SANTA CLARA — DIÁRIO → MENSAL → ANUAL
-- ============================================================
--
-- Objetivo:
-- Apresentar, query a query, a proveniência registrada no SQLite para o cenário
-- em que dados diários de janeiro são agregados em um mensal, depois em 12
-- representações mensais e, por fim, em um agregado anual usado no cálculo.
--
-- Fazenda / personagem: Fazenda Santa Clara
-- Granularidade: daily (jan) → monthly_aggregation_january → 12 monthly → annual_aggregation
--
-- Fluxo da pipeline (ordem deste arquivo):
--   1. Identificação da execução
--   2. Entrada de dados brutos
--   3. Wrapper e normalização
--   4. Integração semântica e ontologia
--   5. Agregação
--   6. Cálculo e resultado preliminar
--   7. Aprovação humana e publicação final
--   8. Hashes e blockchain simulado
--   9. Relações formais de proveniência
--  10. Linhagem completa do caso
--
-- Observação:
-- Apenas consultas SELECT. Não há INSERT, UPDATE ou DELETE.
--
-- Pré-requisito:
--   python scripts/demo_repository_full_population/run_all.py
--
-- Execução sugerida:
--   sqlite3 data/provenance.db < scripts/demo_repository_full_population/queries_03_daily_to_monthly_to_annual_pipeline.sql
--
-- Filtros de referência (demo):
--   Diários janeiro:  run_code LIKE 'demo_repo_santa_clara_2026-01-%' AND NOT LIKE '%-agg%'
--   Agregado jan:     demo_repo_santa_clara_2026-m01-agg
--   Mensais (m01..m12): demo_repo_santa_clara_2026-m%-agg
--   Anual:            demo_repo_santa_clara_2026-annual


-- ============================================================
-- 1. IDENTIFICAÇÃO DA EXECUÇÃO DA PIPELINE
-- ============================================================

-- ------------------------------------------------------------
-- Etapa 1 — Mapa de execuções (pipeline_run) do caso
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Todos os pipeline_run da Fazenda Santa Clara no demo: 31 diários de janeiro,
-- runs mensais agregados (m01..m12) e o run anual de consolidação/cálculo.
--
-- Por que isso importa:
-- Cada granularidade tem seu próprio pipeline_run; isso permite rastrear
-- proveniência por período sem misturar linhagens operacionais.
--
-- Como interpretar:
-- Espere ~31 linhas com padrão 2026-01-NN, até 12 linhas demo_repo_santa_clara_2026-mNN-agg
-- e uma linha demo_repo_santa_clara_2026-annual. reporting_period_reference indica o período lógico.
SELECT
    r.pipeline_run_id AS id_execucao_pipeline,
    r.run_code AS codigo_execucao,
    r.farm_reference AS fazenda,
    r.reporting_period_reference AS periodo_referencia,
    r.run_status AS status_execucao,
    r.started_at AS inicio_execucao,
    r.parent_pipeline_run_id AS id_execucao_pai
FROM pipeline_pipeline_run AS r
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026%'
ORDER BY r.reporting_period_reference, r.run_code;


-- ------------------------------------------------------------
-- Etapa 2 — Bundles de proveniência por execução
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Bundles PROV (pipeline_run, wrapper, semantic, calculation, publication)
-- agrupando entidades e atividades de cada run.
--
-- Por que isso importa:
-- O modelo W3C PROV organiza o grafo em pacotes coerentes por fase da pipeline,
-- facilitando auditoria e apresentação por etapa.
--
-- Como interpretar:
-- Cada run_code deve aparecer com vários bundle_type. Runs diários tendem a ter
-- bundles de wrapper e semantic; o run anual concentra calculation e publication.
SELECT
    r.run_code AS codigo_execucao,
    b.bundle_type AS tipo_bundle,
    b.status AS status_bundle,
    b.name AS nome_bundle,
    b.created_at AS criado_em
FROM prov_core_prov_bundle AS b
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = b.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026%'
ORDER BY r.run_code, b.bundle_type;


-- ------------------------------------------------------------
-- Etapa 3 — Agentes envolvidos (disparo, agregação, revisão)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Agentes humanos e de software registrados no demo (trigger, revisor, agregador).
--
-- Por que isso importa:
-- Proveniência exige atribuição de responsabilidade: quem disparou o fluxo,
-- quem aprovou o resultado e qual componente executou agregações.
--
-- Como interpretar:
-- Três agentes típicos com external_reference prefixado em demo:. O revisor aparece
-- depois na seção 7 via associated_with na atividade de review.
SELECT
    ag.agent_id AS id_agente,
    ag.agent_type AS tipo_agente,
    ag.name AS nome_agente,
    ag.external_reference AS referencia_externa
FROM prov_core_prov_agent AS ag
WHERE ag.external_reference LIKE 'demo:%'
ORDER BY ag.agent_type, ag.name;


-- ============================================================
-- 2. ENTRADA DE DADOS BRUTOS
-- ============================================================

-- ------------------------------------------------------------
-- Etapa 4 — Artefatos brutos diários (31 dias de janeiro)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Os 31 source_artifact de janeiro: arquivo original, hash e vínculo à entidade PROV.
--
-- Por que isso importa:
-- São a matéria-prima da cadeia; toda linhagem posterior deriva destes registros
-- (direta ou via agregações).
--
-- Como interpretar:
-- Deve retornar 31 linhas ordenadas por run_code (2026-01-01 .. 2026-01-31).
-- content_hash permite verificar integridade do bruto antes do wrapper.
SELECT
    r.run_code AS codigo_execucao,
    r.reporting_period_reference AS dia_referencia,
    sa.source_artifact_id AS id_artefato_bruto,
    sa.original_filename AS arquivo_original,
    sa.source_system AS sistema_origem,
    sa.content_hash AS hash_conteudo,
    sa.received_at AS recebido_em,
    sa.prov_entity_id AS id_entidade_prov_bruto
FROM pipeline_source_artifact AS sa
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sa.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%'
  AND r.run_code NOT LIKE '%-agg%'
ORDER BY r.run_code;


-- ============================================================
-- 3. WRAPPER E NORMALIZAÇÃO
-- ============================================================

-- ------------------------------------------------------------
-- Etapa 5 — Definição de wrapper utilizada
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Catálogo wrapper_definition referenciado pelas execuções diárias do caso.
--
-- Por que isso importa:
-- Documenta qual transformação (layout/versão) converte bruto em lote normalizado,
-- essencial para reprodutibilidade e auditoria de método.
--
-- Como interpretar:
-- Normalmente uma linha (demo-repo-normalizer). Se vazio, o demo ainda não foi executado.
SELECT
    wd.wrapper_definition_id AS id_definicao_wrapper,
    wd.wrapper_name AS nome_wrapper,
    wd.wrapper_version AS versao_wrapper,
    wd.source_layout_name AS layout_fonte,
    wd.code_hash AS hash_codigo_wrapper
FROM pipeline_wrapper_definition AS wd
WHERE wd.wrapper_name = 'demo-repo-normalizer';


-- ------------------------------------------------------------
-- Etapa 6 — Execuções de wrapper (31 dias)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Cada wrapper_execution ligada a um artefato bruto diário e a uma atividade PROV.
--
-- Por que isso importa:
-- Registra o momento em que o dado bruto foi transformado; é a segunda etapa
-- operacional da pipeline.
--
-- Como interpretar:
-- 31 linhas com execution_status = succeeded. input_artifact_id aponta ao bruto do mesmo dia.
SELECT
    r.run_code AS codigo_execucao,
    we.wrapper_execution_id AS id_execucao_wrapper,
    we.execution_status AS status_wrapper,
    we.started_at AS inicio_wrapper,
    we.finished_at AS fim_wrapper,
    we.input_artifact_id AS id_artefato_entrada,
    we.prov_activity_id AS id_atividade_prov_wrapper
FROM pipeline_wrapper_execution AS we
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = we.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%'
  AND r.run_code NOT LIKE '%-agg%'
ORDER BY r.run_code;


-- ------------------------------------------------------------
-- Etapa 7 — Lotes normalizados gerados (31 dias)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- normalized_batch por dia: código do lote, contagem de registros e hash.
--
-- Por que isso importa:
-- É o insumo da integração semântica; prova que o wrapper produziu saída estruturada
-- auditável antes da canonização.
--
-- Como interpretar:
-- 31 linhas; record_count tipicamente 1 por dia no demo. batch_code identifica o lote no run.
SELECT
    r.run_code AS codigo_execucao,
    nb.normalized_batch_id AS id_lote_normalizado,
    nb.batch_code AS codigo_lote,
    nb.schema_version AS versao_schema,
    nb.record_count AS quantidade_registros,
    nb.content_hash AS hash_lote,
    nb.generated_at AS gerado_em,
    nb.prov_entity_id AS id_entidade_prov_lote
FROM pipeline_normalized_batch AS nb
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = nb.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%'
  AND r.run_code NOT LIKE '%-agg%'
ORDER BY r.run_code;


-- ------------------------------------------------------------
-- Etapa 8 — PROV: wrapper consumiu bruto (used)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Relações prov_core_prov_used entre atividade de wrapper e entidade source_artifact.
--
-- Por que isso importa:
-- Formaliza em PROV que o wrapper *usou* o dado bruto — não apenas correlação por FK.
--
-- Como interpretar:
-- Liste detalhada (amostra) ou contagem total 31. role costuma indicar o papel do insumo.
SELECT
    r.run_code AS codigo_execucao,
    a.name AS nome_atividade,
    e.name AS entidade_consumida,
    e.entity_type AS tipo_entidade,
    u.role AS papel_uso,
    u.used_at AS usado_em
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%'
  AND r.run_code NOT LIKE '%-agg%'
  AND a.activity_type = 'wrapper_execution'
ORDER BY r.run_code;


-- ------------------------------------------------------------
-- Etapa 9 — PROV: wrapper gerou lote normalizado (generated)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Relações prov_core_prov_generated da atividade de wrapper para entidade normalized_batch.
--
-- Por que isso importa:
-- Complementa used: prova que a atividade *produziu* o lote normalizado (wasGeneratedBy).
--
-- Como interpretar:
-- Uma linha por dia (31). entidade_gerada deve ser o lote do mesmo run_code.
SELECT
    r.run_code AS codigo_execucao,
    a.name AS nome_atividade,
    e.name AS entidade_gerada,
    e.entity_type AS tipo_entidade,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%'
  AND r.run_code NOT LIKE '%-agg%'
  AND a.activity_type = 'wrapper_execution'
ORDER BY r.run_code;


-- ============================================================
-- 4. INTEGRAÇÃO SEMÂNTICA E ONTOLOGIA
-- ============================================================

-- ------------------------------------------------------------
-- Etapa 10 — Integrações semânticas diárias (31)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- semantic_integration_execution por dia: ontologia, status e lote de entrada.
--
-- Por que isso importa:
-- Registra a atividade que mapeia o lote normalizado para o modelo canônico/ontológico.
--
-- Como interpretar:
-- 31 linhas; normalized_batch_id deve corresponder ao lote do mesmo run diário.
SELECT
    r.run_code AS codigo_execucao,
    sie.semantic_integration_execution_id AS id_integracao_semantica,
    sie.ontology_name AS ontologia,
    sie.ontology_version AS versao_ontologia,
    sie.execution_status AS status_integracao,
    sie.started_at AS inicio_integracao,
    sie.normalized_batch_id AS id_lote_entrada,
    sie.prov_activity_id AS id_atividade_prov_semantica
FROM semantic_semantic_integration_execution AS sie
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sie.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%'
  AND r.run_code NOT LIKE '%-agg%'
ORDER BY r.run_code;


-- ------------------------------------------------------------
-- Etapa 11 — Snapshots canônicos diários (31)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- canonical_snapshot por dia: rótulo, hash do snapshot e entidade PROV associada.
--
-- Por que isso importa:
-- É a base semântica publicada por dia; entradas da agregação mensal de janeiro
-- referenciam estas entidades/snapshots.
--
-- Como interpretar:
-- 31 linhas. snapshot_hash é o identificador de conteúdo canônico do dia.
SELECT
    r.run_code AS codigo_execucao,
    cs.canonical_snapshot_id AS id_snapshot_canonico,
    cs.snapshot_label AS rotulo_snapshot,
    cs.snapshot_hash AS hash_snapshot,
    cs.published_at AS publicado_em,
    cs.prov_entity_id AS id_entidade_prov_snapshot
FROM semantic_canonical_snapshot AS cs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%'
  AND r.run_code NOT LIKE '%-agg%'
ORDER BY r.run_code;


-- ------------------------------------------------------------
-- Etapa 12 — Itens dos snapshots diários
-- ------------------------------------------------------------
-- O que esta query mostra:
-- canonical_snapshot_item: métricas atômicas (ex.: milk_production) por dia.
--
-- Por que isso importa:
-- Detalha o conteúdo quantitativo dentro de cada snapshot canônico diário.
--
-- Como interpretar:
-- Depende do demo ter criado itens por snapshot (esperado 31+ linhas).
-- Se retornar vazio, o run_all pode não ter sido executado ou snapshots sem itens.
SELECT
    r.run_code AS codigo_execucao,
    csi.item_key AS chave_item,
    csi.item_hash AS hash_item,
    csi.payload AS conteudo_item
FROM semantic_canonical_snapshot_item AS csi
INNER JOIN semantic_canonical_snapshot AS cs ON cs.canonical_snapshot_id = csi.canonical_snapshot_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%'
  AND r.run_code NOT LIKE '%-agg%'
ORDER BY r.run_code, csi.item_key;


-- ------------------------------------------------------------
-- Etapa 13 — Publicação canônica na ontologia (links diários)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- ontology_resource_link ligando snapshots diários a URIs ontológicas (estágio canonical_input).
--
-- Por que isso importa:
-- Demonstra publicação dos dados canônicos na ontologia antes do cálculo e das agregações.
--
-- Como interpretar:
-- publication_stage = canonical_input nos runs diários. ontology_uri é identificador RDF.
SELECT
    r.run_code AS codigo_execucao,
    orl.ontology_resource_link_id AS id_link_ontologia,
    orl.ontology_uri AS uri_ontologia,
    orl.rdf_class AS classe_rdf,
    orl.publication_stage AS estagio_publicacao,
    orl.published_at AS publicado_em
FROM semantic_ontology_resource_link AS orl
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = orl.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%'
  AND r.run_code NOT LIKE '%-agg%'
ORDER BY r.run_code;


-- ------------------------------------------------------------
-- Etapa 14 — PROV: integração semântica usou lote (used)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Relações used da atividade semantic_integration sobre normalized_batch.
--
-- Por que isso importa:
-- Prova formalmente que a integração consumiu o lote correto de cada dia.
--
-- Como interpretar:
-- Contagem esperada: 31 relações used com activity_type = semantic_integration nos runs diários.
SELECT
    COUNT(u.used_id) AS total_used_integracao_diaria
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%'
  AND r.run_code NOT LIKE '%-agg%'
  AND a.activity_type = 'semantic_integration';


-- ------------------------------------------------------------
-- Etapa 15 — PROV: integração gerou snapshot canônico (generated)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Relações generated produzindo entidade canonical_snapshot por dia.
--
-- Por que isso importa:
-- Fecha o ciclo semântico diário: lote normalizado → atividade → snapshot canônico.
--
-- Como interpretar:
-- Contagem esperada: 31 relações generated nos runs diários de janeiro.
SELECT
    COUNT(g.generated_id) AS total_generated_snapshot_diario
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%'
  AND r.run_code NOT LIKE '%-agg%'
  AND a.activity_type = 'semantic_integration';


-- ============================================================
-- 5. AGREGAÇÃO
-- ============================================================

-- ------------------------------------------------------------
-- Etapa 16 — Atividade monthly_aggregation_january
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Atividade PROV que consolida os 31 snapshots/entidades diárias de janeiro.
--
-- Por que isso importa:
-- Primeira agregação do caso: reduz granularidade diária → mensal (janeiro).
--
-- Como interpretar:
-- Uma linha no run demo_repo_santa_clara_2026-m01-agg com name = monthly_aggregation_january.
SELECT
    r.run_code AS codigo_execucao,
    a.activity_id AS id_atividade,
    a.name AS nome_atividade,
    a.activity_type AS tipo_atividade,
    a.status AS status_atividade,
    a.started_at AS inicio_atividade,
    a.ended_at AS fim_atividade
FROM prov_core_prov_activity AS a
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-m01-agg'
  AND a.name = 'monthly_aggregation_january';


-- ------------------------------------------------------------
-- Etapa 17 — Entradas da agregação mensal de janeiro (lista)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Cada entidade/snapshot diário usado como entrada da monthly_aggregation_january.
--
-- Por que isso importa:
-- Evidência auditável de que os 31 dias entraram na agregação (não só contagem).
--
-- Como interpretar:
-- 31 linhas com papel aggregation_input. fonte_diaria identifica o snapshot de origem.
SELECT
    u.used_id AS id_relacao_used,
    se.name AS entidade_fonte_diaria,
    se.entity_type AS tipo_entidade_fonte,
    u.role AS papel_na_agregacao,
    u.used_at AS usado_em
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS se ON se.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-m01-agg'
  AND a.name = 'monthly_aggregation_january'
ORDER BY u.used_at;


-- ------------------------------------------------------------
-- Etapa 18 — Validação: monthly_aggregation_january com 31 entradas
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Contagem de entradas used na agregação mensal de janeiro.
--
-- Por que isso importa:
-- Confirma invariante do caso: janeiro agrega exatamente 31 dias.
--
-- Como interpretar:
-- Coluna total_entradas deve ser 31. Qualquer outro valor indica demo incompleto ou filtro incorreto.
SELECT
    COUNT(u.used_id) AS total_entradas_mensal_janeiro
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-m01-agg'
  AND a.name = 'monthly_aggregation_january';


-- ------------------------------------------------------------
-- Etapa 19 — Entidade monthly_aggregate_january
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Entidade PROV agregada de janeiro (entity_kind monthly-aggregation-january).
--
-- Por que isso importa:
-- Produto intermediário usado na agregação anual junto com os outros 11 meses.
--
-- Como interpretar:
-- Uma linha no run m01-agg. metadata (JSON) pode referenciar canonical_snapshot_id agregado.
SELECT
    e.entity_id AS id_entidade_agregada,
    e.entity_kind AS tipo_agregado,
    e.name AS nome_entidade,
    e.content_hash AS hash_entidade,
    e.metadata AS metadados
FROM prov_core_prov_entity AS e
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = e.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-m01-agg'
  AND e.entity_kind = 'monthly-aggregation-january';


-- ------------------------------------------------------------
-- Etapa 20 — PROV: monthly_aggregate gerado e derivado dos 31 dias
-- ------------------------------------------------------------
-- O que esta query mostra:
-- generated (agregação → entidade mensal) e derived_from (mensal ← diários).
--
-- Por que isso importa:
-- Estabelece linhagem formal rollup diário → mensal antes do rollup anual.
--
-- Como interpretar:
-- generated: 1 linha. derived_from: 31 linhas com derivation_type = monthly_aggregation_january.
SELECT
    g.generated_id AS id_generated,
    ge.name AS entidade_agregada_jan,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS ge ON ge.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-m01-agg'
  AND a.name = 'monthly_aggregation_january';

SELECT
    d.derived_id AS id_derived_from,
    se.name AS fonte_diaria,
    ge.name AS agregado_mensal_jan,
    d.derivation_type AS tipo_derivacao
FROM prov_core_prov_derived_from AS d
INNER JOIN prov_core_prov_entity AS ge ON ge.entity_id = d.generated_entity_id
INNER JOIN prov_core_prov_entity AS se ON se.entity_id = d.source_entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ge.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-m01-agg'
  AND d.derivation_type = 'monthly_aggregation_january'
ORDER BY se.name;


-- ------------------------------------------------------------
-- Etapa 21 — Representações mensais (m01..m12) para agregação anual
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Snapshots canônicos nos runs mensais demo_repo_santa_clara_2026-mNN-agg (12 meses).
--
-- Por que isso importa:
-- São as 12 entradas da annual_aggregation (janeiro agregado + fev..dez representativos).
--
-- Como interpretar:
-- 12 linhas ordenadas por run_code. Janeiro é m01-agg; demais meses têm ingestão simplificada no demo.
SELECT
    r.run_code AS codigo_execucao,
    r.reporting_period_reference AS mes_referencia,
    cs.canonical_snapshot_id AS id_snapshot_mensal,
    cs.snapshot_label AS rotulo_snapshot
FROM semantic_canonical_snapshot AS cs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-m%'
ORDER BY r.run_code;


-- ------------------------------------------------------------
-- Etapa 22 — Atividade annual_aggregation
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Atividade PROV annual_aggregation no run anual.
--
-- Por que isso importa:
-- Segunda agregação: consolida 12 insumos mensais antes do cálculo GHG.
--
-- Como interpretar:
-- Uma linha em demo_repo_santa_clara_2026-annual com name = annual_aggregation.
SELECT
    r.run_code AS codigo_execucao,
    a.activity_id AS id_atividade,
    a.name AS nome_atividade,
    a.started_at AS inicio_atividade,
    a.ended_at AS fim_atividade
FROM prov_core_prov_activity AS a
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
  AND a.name = 'annual_aggregation';


-- ------------------------------------------------------------
-- Etapa 23 — Entradas da annual_aggregation (lista das 12 mensais)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Cada entidade mensal consumida pela agregação anual.
--
-- Por que isso importa:
-- Prova rastreabilidade dos 12 meses até o agregado anual usado no cálculo.
--
-- Como interpretar:
-- 12 linhas. fonte_mensal deve corresponder a snapshots dos runs m01..m12.
SELECT
    u.used_id AS id_relacao_used,
    se.name AS entidade_fonte_mensal,
    se.entity_kind AS tipo_fonte,
    u.role AS papel,
    u.used_at AS usado_em
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS se ON se.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
  AND a.name = 'annual_aggregation'
ORDER BY u.used_at;


-- ------------------------------------------------------------
-- Etapa 24 — Validação: annual_aggregation com 12 entradas
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Contagem de entradas used na agregação anual.
--
-- Por que isso importa:
-- Invariante do caso mensal→anual: exatamente 12 meses no rollup.
--
-- Como interpretar:
-- total_entradas_mensais deve ser 12.
SELECT
    COUNT(u.used_id) AS total_entradas_mensais
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
  AND a.name = 'annual_aggregation';


-- ------------------------------------------------------------
-- Etapa 25 — Entidade annual_aggregate e snapshot canônico do run anual
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Entidade annual-aggregation e o canonical_snapshot do run anual (base do cálculo).
--
-- Por que isso importa:
-- O cálculo não consome os 31 dias diretamente; consome o agregado/snapshot anual.
--
-- Como interpretar:
-- entity_kind annual-aggregation na mesma execução do snapshot usado em calculation_execution.
SELECT
    e.entity_id AS id_entidade_agregada_anual,
    e.entity_kind AS tipo_agregado,
    e.name AS nome_entidade,
    cs.canonical_snapshot_id AS id_snapshot_anual,
    cs.snapshot_label AS rotulo_snapshot_anual,
    cs.snapshot_hash AS hash_snapshot_anual
FROM prov_core_prov_entity AS e
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = e.pipeline_run_id
LEFT JOIN semantic_canonical_snapshot AS cs ON cs.pipeline_run_id = r.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
  AND e.entity_kind = 'annual-aggregation';


-- ------------------------------------------------------------
-- Etapa 26 — PROV: annual_aggregate derivado dos 12 meses
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Relações derived_from ligando agregado anual às 12 fontes mensais.
--
-- Por que isso importa:
-- Fecha a cadeia rollup: 31 dias → jan mensal → 12 meses → anual.
--
-- Como interpretar:
-- 12 linhas com derivation_type = annual_aggregation no run anual.
SELECT
    d.derived_id AS id_derived_from,
    se.name AS fonte_mensal,
    ge.name AS agregado_anual,
    d.derivation_type AS tipo_derivacao
FROM prov_core_prov_derived_from AS d
INNER JOIN prov_core_prov_entity AS ge ON ge.entity_id = d.generated_entity_id
INNER JOIN prov_core_prov_entity AS se ON se.entity_id = d.source_entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ge.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
  AND d.derivation_type = 'annual_aggregation'
ORDER BY se.name;


-- ============================================================
-- 6. CÁLCULO E RESULTADO PRELIMINAR
-- ============================================================

-- ------------------------------------------------------------
-- Etapa 27 — Método e versão de cálculo
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_method e calculation_method_version usados no demo (catálogo compartilhado).
--
-- Por que isso importa:
-- Define qual metodologia GHG e qual versão foram aplicadas ao snapshot anual.
--
-- Como interpretar:
-- method_code demo-repo-ghg-2026 com version_label 1.0.0 e status active.
SELECT
    cm.method_code AS codigo_metodo,
    cm.method_name AS nome_metodo,
    cmv.version_label AS versao_metodo,
    cmv.status AS status_versao
FROM calculation_calculation_method AS cm
INNER JOIN calculation_calculation_method_version AS cmv
    ON cmv.calculation_method_id = cm.calculation_method_id
WHERE cm.method_code = 'demo-repo-ghg-2026';


-- ------------------------------------------------------------
-- Etapa 28 — Conjunto e valores de parâmetros (run anual)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_parameter_set e parameter_value do run anual.
--
-- Por que isso importa:
-- Parâmetros travados (ex.: aggregation_inputs = 12) documentam premissas do cálculo.
--
-- Como interpretar:
-- parameter_set_status locked/approved. aggregation_inputs deve refletir 12 entradas mensais.
SELECT
    cps.calculation_parameter_set_id AS id_conjunto_parametros,
    cps.parameter_set_status AS status_conjunto,
    cpv.parameter_name AS nome_parametro,
    cpv.parameter_value_numeric AS valor_numerico,
    cpv.parameter_value_text AS valor_texto,
    cpv.parameter_unit AS unidade
FROM calculation_calculation_parameter_set AS cps
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cps.pipeline_run_id
LEFT JOIN calculation_calculation_parameter_value AS cpv
    ON cpv.calculation_parameter_set_id = cps.calculation_parameter_set_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual';


-- ------------------------------------------------------------
-- Etapa 29 — Execução do cálculo sobre base canônica anual
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_execution: liga método, parâmetros e canonical_snapshot do run anual.
--
-- Por que isso importa:
-- Registra a atividade de cálculo propriamente dita sobre o agregado anual.
--
-- Como interpretar:
-- Uma execução no run anual. canonical_snapshot_id aponta ao snapshot agregado, não aos 31 diários.
SELECT
    ce.calculation_execution_id AS id_execucao_calculo,
    ce.execution_status AS status_calculo,
    ce.started_at AS inicio_calculo,
    ce.finished_at AS fim_calculo,
    ce.canonical_snapshot_id AS id_snapshot_entrada,
    ce.prov_activity_id AS id_atividade_prov_calculo
FROM calculation_calculation_execution AS ce
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ce.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual';


-- ------------------------------------------------------------
-- Etapa 30 — PROV: cálculo usou snapshot/agregado anual (used)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Entidade consumida pela atividade calculation_execution no run anual.
--
-- Por que isso importa:
-- Evidência PROV de que o cálculo usou o agregado anual — não os 31 registros diários isolados.
--
-- Como interpretar:
-- entity_type canonical_snapshot ou entidade ligada ao agregado. Uma linha principal de insumo.
SELECT
    e.entity_id AS id_entidade_usada,
    e.entity_type AS tipo_entidade,
    e.name AS nome_entidade,
    e.entity_kind AS kind_entidade,
    u.role AS papel
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
  AND a.activity_type = 'calculation_execution';


-- ------------------------------------------------------------
-- Etapa 31 — Result set preliminar
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_result_set gerado pela execução (status evolui após revisão humana).
--
-- Por que isso importa:
-- Armazena o resultado quantitativo antes da aprovação e publicação final.
--
-- Como interpretar:
-- result_set_status preliminary até review approved; depois approved. summary_hash para integridade.
SELECT
    rs.calculation_result_set_id AS id_conjunto_resultado,
    rs.result_set_status AS status_resultado,
    rs.generated_at AS gerado_em,
    rs.summary_hash AS hash_resumo
FROM calculation_calculation_result_set AS rs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual';


-- ------------------------------------------------------------
-- Etapa 32 — Itens de resultado (métricas)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_result_item: valores como aggregated_milk_production.
--
-- Por que isso importa:
-- Apresenta o número final auditável derivado da cadeia de agregações.
--
-- Como interpretar:
-- result_name aggregated_milk_production com result_unit em litros no demo.
SELECT
    ri.result_name AS nome_metrica,
    ri.result_type AS tipo_resultado,
    ri.result_value AS valor,
    ri.result_unit AS unidade
FROM calculation_calculation_result_item AS ri
INNER JOIN calculation_calculation_result_set AS rs
    ON rs.calculation_result_set_id = ri.calculation_result_set_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual';


-- ------------------------------------------------------------
-- Etapa 33 — PROV: resultado gerado pelo cálculo (generated)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Relação generated da atividade de cálculo para entidade result_set.
--
-- Por que isso importa:
-- Formaliza que o resultado preliminar foi *produzido* pela atividade de cálculo.
--
-- Como interpretar:
-- Uma linha ligando calculation_execution ao result_set do run anual.
SELECT
    g.generated_id AS id_generated,
    a.name AS atividade_calculo,
    e.name AS entidade_resultado,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
  AND a.activity_type = 'calculation_execution';


-- ============================================================
-- 7. APROVAÇÃO HUMANA E PUBLICAÇÃO FINAL
-- ============================================================

-- ------------------------------------------------------------
-- Etapa 34 — Revisão humana (aprovação)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_review com decision, comentário e revisor.
--
-- Por que isso importa:
-- Gate de governança: resultado só pode ser publicado após aprovação explícita.
--
-- Como interpretar:
-- decision = approved. reviewer_agent_id aponta para agente humano do demo.
SELECT
    cr.calculation_review_id AS id_revisao,
    cr.decision AS decisao_revisor,
    cr.review_comment AS comentario_revisao,
    cr.reviewed_at AS revisado_em,
    cr.reviewer_agent_id AS id_agente_revisor,
    ag.name AS nome_revisor
FROM calculation_calculation_review AS cr
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cr.pipeline_run_id
LEFT JOIN prov_core_prov_agent AS ag ON ag.agent_id = cr.reviewer_agent_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual';


-- ------------------------------------------------------------
-- Etapa 35 — PROV: revisão usou resultado e associou revisor
-- ------------------------------------------------------------
-- O que esta query mostra:
-- used (review → result_set) e associated_with (review → agente revisor).
--
-- Por que isso importa:
-- Atribui responsabilidade humana e liga formalmente revisão ao artefato revisado.
--
-- Como interpretar:
-- Uma linha em prov_used com role reviewed_result_set; uma em associated_with com role reviewer.
SELECT
    u.used_id AS id_used_revisao,
    e.name AS resultado_revisado,
    u.role AS papel
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
  AND a.activity_type = 'calculation_review';

SELECT
    aw.association_id AS id_associacao,
    ag.name AS agente_revisor,
    aw.role AS papel_agente
FROM prov_core_prov_associated_with AS aw
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = aw.activity_id
INNER JOIN prov_core_prov_agent AS ag ON ag.agent_id = aw.agent_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
  AND a.activity_type = 'calculation_review';


-- ------------------------------------------------------------
-- Etapa 36 — Publicação final do resultado aprovado
-- ------------------------------------------------------------
-- O que esta query mostra:
-- result_publication_execution publicando resultado aprovado na ontologia.
--
-- Por que isso importa:
-- Última etapa funcional da pipeline antes de hash e ancoragem simulada.
--
-- Como interpretar:
-- publication_status published. calculation_review_id deve estar preenchido.
SELECT
    pe.result_publication_execution_id AS id_publicacao,
    pe.publication_status AS status_publicacao,
    pe.published_at AS publicado_em,
    pe.target_graph_name AS grafo_destino,
    pe.calculation_review_id AS id_revisao_vinculada
FROM calculation_result_publication_execution AS pe
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = pe.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual';


-- ------------------------------------------------------------
-- Etapa 37 — Link ontológico da publicação final (se gerado)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- ontology_resource_link no estágio publication_final ligado ao run anual.
--
-- Por que isso importa:
-- Demonstra publicação do resultado aprovado no grafo/ontologia de destino.
--
-- Como interpretar:
-- Pode haver 0 ou 1 linha conforme create_ontology_resource_link no recorder.
-- Se vazio, a publicação ainda existe em result_publication_execution.
SELECT
    orl.ontology_resource_link_id AS id_link,
    orl.ontology_uri AS uri_ontologia,
    orl.publication_stage AS estagio,
    orl.published_at AS publicado_em
FROM semantic_ontology_resource_link AS orl
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = orl.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
  AND orl.publication_stage IN ('publication_final', 'final');


-- ============================================================
-- 8. HASHES E BLOCKCHAIN
-- ============================================================

-- ------------------------------------------------------------
-- Etapa 38 — Registros de hash (integridade)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- audit_hash_record por subject_kind no run anual e artefatos relacionados.
--
-- Por que isso importa:
-- Permite verificar integridade de snapshots, result sets e outros sujeitos críticos.
--
-- Como interpretar:
-- Várias linhas por subject_kind (canonical_snapshot, calculation_result_set, normalized_batch, etc.).
SELECT
    hr.hash_record_id AS id_hash,
    hr.subject_kind AS tipo_sujeito,
    hr.subject_id AS id_sujeito,
    hr.hash_algorithm AS algoritmo,
    hr.hash_value AS valor_hash,
    hr.computed_at AS calculado_em
FROM audit_hash_record AS hr
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = hr.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
ORDER BY hr.subject_kind, hr.computed_at;


-- ------------------------------------------------------------
-- Etapa 39 — Ancoragem blockchain simulada
-- ------------------------------------------------------------
-- O que esta query mostra:
-- audit_blockchain_anchor ligado a hash_record (demo-chain, transaction_hash simulado).
--
-- Por que isso importa:
-- Simula compromisso externo do hash sem blockchain real; útil para narrativa de auditoria.
--
-- Como interpretar:
-- anchor_status confirmed e transaction_hash prefixado demo-tx-. metadata indica simulated=true no demo.
SELECT
    ba.blockchain_anchor_id AS id_ancora,
    ba.blockchain_network AS rede,
    ba.transaction_hash AS id_transacao_simulada,
    ba.anchor_status AS status_ancora,
    ba.anchored_at AS ancorado_em,
    hr.subject_kind AS tipo_sujeito_hash,
    hr.hash_value AS hash_ancorado
FROM audit_blockchain_anchor AS ba
INNER JOIN audit_hash_record AS hr ON hr.hash_record_id = ba.hash_record_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ba.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual';


-- ------------------------------------------------------------
-- Etapa 40 — Eventos de auditoria complementares
-- ------------------------------------------------------------
-- O que esta query mostra:
-- audit_audit_event (ex.: review, agregação, demo.*) ligados ao caso.
--
-- Por que isso importa:
-- Trilha adicional além do ledger operacional e outbox.
--
-- Como interpretar:
-- event_type como calculation_review.approved ou demo.*. Pode incluir eventos de outros runs do demo.
SELECT
    ae.audit_event_id AS id_evento,
    ae.event_type AS tipo_evento,
    ae.subject_kind AS tipo_sujeito,
    ae.recorded_at AS registrado_em
FROM audit_audit_event AS ae
WHERE ae.event_type LIKE 'demo.%'
   OR ae.event_type LIKE 'calculation_review.%'
ORDER BY ae.recorded_at DESC
LIMIT 20;


-- ------------------------------------------------------------
-- Etapa 41 — Eventos de outbox (integração assíncrona)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- audit_outbox_event gerados durante gravações (status pending/published).
--
-- Por que isso importa:
-- Mostra que o serviço emitiu eventos de domínio para relay/downstream.
--
-- Como interpretar:
-- Muitos eventos no demo global; filtre mentalmente por aggregate_kind do run anual se necessário.
SELECT
    oe.outbox_event_id AS id_outbox,
    oe.aggregate_kind AS tipo_agregado,
    oe.event_type AS tipo_evento,
    oe.status AS status_outbox,
    oe.created_at AS criado_em
FROM audit_outbox_event AS oe
WHERE oe.aggregate_kind IN (
    'pipeline_run',
    'canonical_snapshot',
    'calculation_result_set',
    'blockchain_anchor'
)
ORDER BY oe.created_at DESC
LIMIT 25;


-- ============================================================
-- 9. RELAÇÕES FORMAIS DE PROVENIÊNCIA
-- ============================================================

-- ------------------------------------------------------------
-- Etapa 42 — Todas as relações used do caso Santa Clara
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Visão consolidada de prov_core_prov_used em todos os runs do caso.
--
-- Por que isso importa:
-- Mapa de consumo: wrapper, semântica, agregações, cálculo, revisão, publicação.
--
-- Como interpretar:
-- Ordene por codigo_execucao e nome_atividade para seguir a narrativa temporal.
SELECT
    r.run_code AS codigo_execucao,
    a.activity_type AS tipo_atividade,
    a.name AS nome_atividade,
    u.role AS papel,
    e.entity_type AS tipo_entidade_entrada,
    e.name AS nome_entidade_entrada,
    u.used_at AS usado_em
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026%'
ORDER BY r.run_code, a.name, u.used_at;


-- ------------------------------------------------------------
-- Etapa 43 — Todas as relações generated do caso
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Entidades produzidas por atividades (wasGeneratedBy).
--
-- Por que isso importa:
-- Identifica saídas de cada fase: lote, snapshot, agregados, resultado.
--
-- Como interpretar:
-- Inclui generated de agregações (entidades monthly/annual-aggregation) e de cálculo.
SELECT
    r.run_code AS codigo_execucao,
    a.name AS nome_atividade,
    e.entity_type AS tipo_entidade_saida,
    e.entity_kind AS kind_entidade_saida,
    e.name AS nome_entidade_saida,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026%'
ORDER BY r.run_code, g.generated_at;


-- ------------------------------------------------------------
-- Etapa 44 — Todas as relações derived_from do caso
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Derivações explícitas (wrapper, semântica, monthly_aggregation_january, annual_aggregation).
--
-- Por que isso importa:
-- Prova rollup e encadeamento entre granularidades.
--
-- Como interpretar:
-- derivation_type distingue normalização, integração semântica e agregações.
SELECT
    r.run_code AS codigo_execucao_execucao_entidade_gerada,
    d.derivation_type AS tipo_derivacao,
    se.name AS entidade_fonte,
    ge.name AS entidade_gerada
FROM prov_core_prov_derived_from AS d
INNER JOIN prov_core_prov_entity AS ge ON ge.entity_id = d.generated_entity_id
INNER JOIN prov_core_prov_entity AS se ON se.entity_id = d.source_entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ge.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026%'
ORDER BY r.run_code, d.derivation_type;


-- ------------------------------------------------------------
-- Etapa 45 — Todas as relações associated_with do caso
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Agentes associados a atividades (ex.: revisor na review).
--
-- Por que isso importa:
-- Atribuição de responsabilidade humana em etapas críticas.
--
-- Como interpretar:
-- Poucas linhas no demo; destaque para calculation_review + agente revisor.
SELECT
    r.run_code AS codigo_execucao,
    a.name AS nome_atividade,
    ag.name AS nome_agente,
    ag.agent_type AS tipo_agente,
    aw.role AS papel
FROM prov_core_prov_associated_with AS aw
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = aw.activity_id
INNER JOIN prov_core_prov_agent AS ag ON ag.agent_id = aw.agent_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026%'
ORDER BY r.run_code, a.name;


-- ------------------------------------------------------------
-- Etapa 46 — Relações revision (caso Santa Clara)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- prov_core_prov_revision no escopo Santa Clara, se existirem.
--
-- Por que isso importa:
-- Este caso principal não usa revisão de entidade como o run de reprocessamento Boa Vista;
-- a query pode retornar zero linhas — isso é esperado.
--
-- Como interpretar:
-- Zero linhas = sem prov_revision neste caso (normal). Reprocessamento está em outro script de demo.
SELECT
    pr.revision_id AS id_revisao,
    pr.revision_reason AS motivo,
    pe.name AS entidade_anterior,
    ne.name AS entidade_nova
FROM prov_core_prov_revision AS pr
INNER JOIN prov_core_prov_entity AS pe ON pe.entity_id = pr.previous_entity_id
INNER JOIN prov_core_prov_entity AS ne ON ne.entity_id = pr.new_entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ne.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026%'
ORDER BY pr.revised_at;


-- ------------------------------------------------------------
-- Etapa 47 — Resumo tabular do grafo PROV (amostra)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- União de used, generated e derived_from para leitura de grafo simplificado.
--
-- Por que isso importa:
-- Apoio visual em apresentação: atividade → entrada → saída por tipo de relação.
--
-- Como interpretar:
-- tipo_relacao distingue used / generated / derived_from. Filtre por codigo_execucao na apresentação.
SELECT
    r.run_code AS codigo_execucao,
    a.name AS atividade,
    'used' AS tipo_relacao,
    e.name AS entidade_relacionada,
    u.role AS detalhe
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026%'
UNION ALL
SELECT
    r.run_code,
    a.name,
    'generated',
    e.name,
    NULL
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026%'
ORDER BY codigo_execucao, tipo_relacao, atividade;


-- ============================================================
-- 10. LINHAGEM COMPLETA DO CASO
-- ============================================================

-- ------------------------------------------------------------
-- Etapa 48 — Contagens por fase da pipeline
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Números-chave do caso: 31 diários, agregação jan, 12 mensais na agregação anual, publicação.
--
-- Por que isso importa:
-- Fechamento quantitativo para banca: prova que invariantes do cenário foram atendidos.
--
-- Como interpretar:
-- diarios_janeiro=31; entradas_agreg_jan=31; entradas_agreg_anual=12; execucoes_calculo_anual=1.
SELECT 'diarios_janeiro' AS fase_pipeline, COUNT(*) AS quantidade
FROM pipeline_pipeline_run AS r
WHERE r.farm_reference = 'Fazenda Santa Clara'
  AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%'
  AND r.run_code NOT LIKE '%-agg%'
UNION ALL
SELECT 'entradas_monthly_aggregation_january', COUNT(u.used_id)
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-m01-agg'
  AND a.name = 'monthly_aggregation_january'
UNION ALL
SELECT 'entradas_annual_aggregation', COUNT(u.used_id)
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
  AND a.name = 'annual_aggregation'
UNION ALL
SELECT 'execucoes_calculo_run_anual', COUNT(ce.calculation_execution_id)
FROM calculation_calculation_execution AS ce
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ce.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual'
UNION ALL
SELECT 'publicacoes_finais', COUNT(pe.result_publication_execution_id)
FROM calculation_result_publication_execution AS pe
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = pe.pipeline_run_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual';


-- ------------------------------------------------------------
-- Etapa 49 — Linhagem resumida ponta a ponta (run anual como desfecho)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Sequência narrativa das etapas principais até hash e blockchain no run anual.
--
-- Por que isso importa:
-- Uma única consulta para contar a história completa na apresentação final.
--
-- Como interpretar:
-- ordem_etapa crescente; observacao descreve cada elo. Granularidade diária aparece nas fases 1–4 implicitamente via contagens anteriores.
SELECT 1 AS ordem_etapa, 'entrada_bruta_diaria' AS etapa_pipeline, '31 source_artifacts janeiro' AS observacao
UNION ALL SELECT 2, 'wrapper_e_normalizacao', '31 wrapper_execution + 31 normalized_batch'
UNION ALL SELECT 3, 'integracao_semantica', '31 semantic_integration + 31 canonical_snapshot'
UNION ALL SELECT 4, 'publicacao_canonica_diaria', 'ontology_resource_link canonical_input por dia'
UNION ALL SELECT 5, 'agregacao_mensal_jan', 'monthly_aggregation_january com 31 entradas'
UNION ALL SELECT 6, 'agregacao_anual', 'annual_aggregation com 12 entradas mensais'
UNION ALL SELECT 7, 'calculo', 'calculation_execution sobre snapshot do run anual'
UNION ALL SELECT 8, 'resultado_preliminar', 'calculation_result_set + items'
UNION ALL SELECT 9, 'aprovacao_humana', 'calculation_review approved'
UNION ALL SELECT 10, 'publicacao_final', 'result_publication_execution published'
UNION ALL SELECT 11, 'hash_e_blockchain', 'audit_hash_record + audit_blockchain_anchor demo-chain'
ORDER BY ordem_etapa;


-- ------------------------------------------------------------
-- Etapa 50 — Cadeia operacional do run anual (join spine)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Encadeamento técnico no run anual: snapshot agregado → cálculo → resultado → publicação → hash.
--
-- Por que isso importa:
-- Demonstra o desfecho operacional após todas as agregações, em uma linha lógica de FKs.
--
-- Como interpretar:
-- Uma linha quando o demo está completo. status_resultado deve evoluir para approved após revisão.
SELECT
    r.run_code AS codigo_execucao,
    cs.snapshot_label AS snapshot_agregado_anual,
    ce.calculation_execution_id AS id_calculo,
    rs.result_set_status AS status_resultado,
    cr.decision AS decisao_revisao,
    pe.publication_status AS status_publicacao,
    hr.hash_value AS hash_resultado,
    ba.transaction_hash AS transacao_blockchain_simulada
FROM pipeline_pipeline_run AS r
LEFT JOIN semantic_canonical_snapshot AS cs ON cs.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_calculation_execution AS ce ON ce.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_calculation_result_set AS rs ON rs.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_calculation_review AS cr ON cr.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_result_publication_execution AS pe ON pe.pipeline_run_id = r.pipeline_run_id
LEFT JOIN audit_hash_record AS hr
    ON hr.pipeline_run_id = r.pipeline_run_id
   AND hr.subject_kind = 'calculation_result_set'
   AND hr.subject_id = rs.calculation_result_set_id
LEFT JOIN audit_blockchain_anchor AS ba ON ba.hash_record_id = hr.hash_record_id
WHERE r.run_code = 'demo_repo_santa_clara_2026-annual';
