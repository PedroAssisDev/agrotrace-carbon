-- ============================================================
-- CASO 2: FAZENDA BOA VISTA — MENSAL PARA ANUAL
-- ============================================================
--
-- Objetivo:
-- Apresentar, query a query, a proveniência registrada no SQLite para este cenário
-- de demonstração, na ordem do fluxo oficial da pipeline.
--
-- Fazenda / personagem: Fazenda Boa Vista
-- Granularidade: monthly (12 runs) → annual_aggregation → cálculo no run anual
--
-- Fluxo da pipeline (ordem deste arquivo):
--   1. Identificação da execução
--   2. Entrada de dados brutos (12 meses)
--   3. Wrapper e normalização (12 meses)
--   4. Integração semântica e ontologia (12 meses)
--   5. Agregação anual (12 → 1)
--   6. Cálculo e resultado preliminar (run anual)
--   7. Aprovação humana e publicação final
--   8. Hashes e blockchain simulado
--   9. Relações formais de proveniência
--   10. Linhagem completa do caso
--
-- Observação:
-- Apenas consultas SELECT. Não há INSERT, UPDATE ou DELETE.
--
-- Pré-requisito:
--   python scripts/demo_repository_full_population/run_all.py
--
-- Execução sugerida:
--   sqlite3 data/provenance.db < scripts/demo_repository_full_population/queries_02_monthly_to_annual_pipeline.sql
--
-- Filtros de referência (demo):
--   Mensais: demo_repo_boa_vista_2026-01 .. 2026-12
--   Anual:  demo_repo_boa_vista_2026-annual


-- ============================================================
-- 1. IDENTIFICAÇÃO DA EXECUÇÃO DA PIPELINE
-- ============================================================


-- ------------------------------------------------------------
-- Etapa 1 — Mapa de execuções (12 mensais + run anual)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Todos os pipeline_run da Fazenda Boa Vista no demo.
--
-- Por que isso importa:
-- Separa processamento mensal da consolidação/cálculo anual.
--
-- Como interpretar:
-- 13 linhas: 12 com run_code 2026-NN e uma linha -annual.
SELECT
    r.pipeline_run_id AS id_execucao_pipeline,
    r.run_code AS codigo_execucao,
    r.reporting_period_reference AS periodo_referencia,
    r.run_status AS status_execucao,
    r.started_at AS inicio_execucao
FROM pipeline_pipeline_run AS r
WHERE r.farm_reference = 'Fazenda Boa Vista'
  AND r.run_code LIKE 'demo_repo_boa_vista_2026%'
ORDER BY r.reporting_period_reference, r.run_code;


-- ------------------------------------------------------------
-- Etapa 2 — Bundles de proveniência por execução
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Bundles PROV em cada run mensal e no run anual.
--
-- Por que isso importa:
-- Organiza o grafo por fase e por período.
--
-- Como interpretar:
-- Runs mensais: wrapper/semantic; run anual: calculation/publication.
SELECT
    r.run_code AS codigo_execucao,
    b.bundle_type AS tipo_bundle,
    b.status AS status_bundle,
    b.created_at AS criado_em
FROM prov_core_prov_bundle AS b
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = b.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista'
  AND r.run_code LIKE 'demo_repo_boa_vista_2026%'
ORDER BY r.run_code, b.bundle_type;


-- ------------------------------------------------------------
-- Etapa 3 — Agentes do demo (disparo, agregação, revisão)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Agentes referenciados no population demo.
--
-- Por que isso importa:
-- Responsabilidade operacional e de aprovação.
--
-- Como interpretar:
-- Filtra external_reference demo:%.
SELECT
    ag.agent_id AS id_agente,
    ag.agent_type AS tipo_agente,
    ag.name AS nome_agente,
    ag.external_reference AS referencia_externa
FROM prov_core_prov_agent AS ag
WHERE ag.external_reference LIKE 'demo:%'
ORDER BY ag.agent_type, ag.name;


-- ============================================================
-- 2. ENTRADA DE DADOS BRUTOS (12 MESES)
-- ============================================================


-- ------------------------------------------------------------
-- Etapa 4 — Artefatos brutos mensais (12 source_artifact)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Um artefato por mês (jan–dez/2026).
--
-- Por que isso importa:
-- Matéria-prima da cadeia e insumo indireto da agregação anual.
--
-- Como interpretar:
-- 12 linhas ordenadas por periodo_referencia.
SELECT
    r.run_code AS codigo_execucao,
    r.reporting_period_reference AS mes_referencia,
    sa.source_artifact_id AS id_artefato_bruto,
    sa.original_filename AS arquivo_original,
    sa.content_hash AS hash_conteudo,
    sa.received_at AS recebido_em
FROM pipeline_source_artifact AS sa
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sa.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
ORDER BY r.reporting_period_reference;


-- ============================================================
-- 3. WRAPPER E NORMALIZAÇÃO (12 MESES)
-- ============================================================


-- ------------------------------------------------------------
-- Etapa 5 — Definição de wrapper utilizada
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Catálogo wrapper_definition do demo.
--
-- Por que isso importa:
-- Mesma transformação em todos os meses.
--
-- Como interpretar:
-- demo-repo-normalizer.
SELECT
    wd.wrapper_name AS nome_wrapper,
    wd.wrapper_version AS versao_wrapper,
    wd.source_layout_name AS layout_fonte
FROM pipeline_wrapper_definition AS wd
WHERE wd.wrapper_name = 'demo-repo-normalizer';


-- ------------------------------------------------------------
-- Etapa 6 — Execuções de wrapper mensais (12)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- wrapper_execution por run mensal.
--
-- Por que isso importa:
-- Transformação bruto → lote em cada mês.
--
-- Como interpretar:
-- 12 linhas succeeded.
SELECT
    r.run_code AS codigo_execucao,
    we.wrapper_execution_id AS id_execucao_wrapper,
    we.execution_status AS status_wrapper,
    we.prov_activity_id AS id_atividade_prov
FROM pipeline_wrapper_execution AS we
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = we.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
ORDER BY r.reporting_period_reference;


-- ------------------------------------------------------------
-- Etapa 7 — Lotes normalizados mensais (12)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- normalized_batch por mês.
--
-- Por que isso importa:
-- Insumo da integração semântica mensal.
--
-- Como interpretar:
-- 12 linhas; record_count tipicamente 1.
SELECT
    r.run_code AS codigo_execucao,
    nb.batch_code AS codigo_lote,
    nb.record_count AS quantidade_registros,
    nb.content_hash AS hash_lote
FROM pipeline_normalized_batch AS nb
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = nb.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
ORDER BY r.reporting_period_reference;


-- ------------------------------------------------------------
-- Etapa 8 — PROV: wrappers consumiram bruto mensal (used)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Lista used wrapper → source_artifact nos 12 meses.
--
-- Por que isso importa:
-- 12 consumos explícitos em PROV.
--
-- Como interpretar:
-- Contagem mental = 12.
SELECT
    r.run_code AS codigo_execucao,
    e.name AS entidade_consumida,
    u.role AS papel_uso
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
  AND a.activity_type = 'wrapper_execution'
ORDER BY r.run_code;


-- ------------------------------------------------------------
-- Etapa 9 — PROV: wrappers geraram lotes mensais (generated)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Lista generated wrapper → normalized_batch.
--
-- Por que isso importa:
-- 12 produções em PROV.
--
-- Como interpretar:
-- Uma por run_code mensal.
SELECT
    r.run_code AS codigo_execucao,
    e.name AS entidade_gerada,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
  AND a.activity_type = 'wrapper_execution'
ORDER BY r.run_code;


-- ============================================================
-- 4. INTEGRAÇÃO SEMÂNTICA E ONTOLOGIA (12 MESES)
-- ============================================================


-- ------------------------------------------------------------
-- Etapa 10 — Integrações semânticas mensais (12)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- semantic_integration_execution por mês.
--
-- Por que isso importa:
-- Produz snapshots canônicos mensais.
--
-- Como interpretar:
-- 12 linhas execution_status succeeded.
SELECT
    r.run_code AS codigo_execucao,
    sie.semantic_integration_execution_id AS id_integracao,
    sie.execution_status AS status_integracao,
    sie.ontology_name AS ontologia
FROM semantic_semantic_integration_execution AS sie
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sie.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
ORDER BY r.reporting_period_reference;


-- ------------------------------------------------------------
-- Etapa 11 — Snapshots canônicos mensais (12)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- canonical_snapshot por mês — entradas da annual_aggregation.
--
-- Por que isso importa:
-- Cada snapshot mensal é insumo da agregação anual.
--
-- Como interpretar:
-- 12 linhas com prov_entity_id distintos.
SELECT
    r.run_code AS codigo_execucao,
    cs.canonical_snapshot_id AS id_snapshot,
    cs.snapshot_label AS rotulo_snapshot,
    cs.snapshot_hash AS hash_snapshot
FROM semantic_canonical_snapshot AS cs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
ORDER BY r.reporting_period_reference;


-- ------------------------------------------------------------
-- Etapa 12 — Itens dos snapshots mensais (amostra)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- canonical_snapshot_item dos 12 meses.
--
-- Por que isso importa:
-- Detalhe de métricas por mês.
--
-- Como interpretar:
-- Várias linhas; ordenado por run e item_key.
SELECT
    r.run_code AS codigo_execucao,
    csi.item_key AS chave_item,
    csi.payload AS conteudo_json
FROM semantic_canonical_snapshot_item AS csi
INNER JOIN semantic_canonical_snapshot AS cs
    ON cs.canonical_snapshot_id = csi.canonical_snapshot_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
ORDER BY r.run_code, csi.item_key;


-- ------------------------------------------------------------
-- Etapa 13 — Links ontológicos canônicos mensais
-- ------------------------------------------------------------
-- O que esta query mostra:
-- ontology_resource_link por run mensal.
--
-- Por que isso importa:
-- Publicação canônica de cada mês.
--
-- Como interpretar:
-- Até 12 linhas.
SELECT
    r.run_code AS codigo_execucao,
    orl.ontology_uri AS uri_ontologia,
    orl.publication_stage AS estagio
FROM semantic_ontology_resource_link AS orl
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = orl.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
ORDER BY r.run_code;


-- ------------------------------------------------------------
-- Etapa 14 — PROV: integrações usaram lotes mensais (used)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- used semantic_integration → normalized_batch (12).
--
-- Por que isso importa:
-- Ligação semântica mensal em PROV.
--
-- Como interpretar:
-- 12 linhas.
SELECT
    r.run_code AS codigo_execucao,
    e.name AS lote_consumido
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
  AND a.activity_type = 'semantic_integration'
ORDER BY r.run_code;


-- ------------------------------------------------------------
-- Etapa 15 — PROV: integrações geraram snapshots mensais (generated)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- generated semantic_integration → canonical_snapshot (12).
--
-- Por que isso importa:
-- Saída semântica mensal formalizada.
--
-- Como interpretar:
-- 12 linhas.
SELECT
    r.run_code AS codigo_execucao,
    e.name AS snapshot_gerado
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
  AND a.activity_type = 'semantic_integration'
ORDER BY r.run_code;


-- ============================================================
-- 5. AGREGAÇÃO ANUAL (12 MENSais → 1 AGREGADO)
-- ============================================================


-- ------------------------------------------------------------
-- Etapa 16 — Atividade annual_aggregation
-- ------------------------------------------------------------
-- O que esta query mostra:
-- prov_activity annual_aggregation no run anual.
--
-- Por que isso importa:
-- Consolida os 12 snapshots mensais.
--
-- Como interpretar:
-- Uma atividade no run demo_repo_boa_vista_2026-annual.
SELECT
    a.activity_id AS id_atividade,
    a.name AS nome_atividade,
    a.status AS status_atividade,
    a.started_at AS inicio,
    a.ended_at AS fim
FROM prov_core_prov_activity AS a
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND a.name = 'annual_aggregation';


-- ------------------------------------------------------------
-- Etapa 17 — Entradas da annual_aggregation (lista das 12 mensais)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- prov_used com role aggregation_input — snapshots mensais.
--
-- Por que isso importa:
-- Evidência lista da cardinalidade da agregação.
--
-- Como interpretar:
-- 12 linhas com nomes dos snapshots fonte.
SELECT
    se.name AS snapshot_mensal_fonte,
    u.role AS papel,
    u.used_at AS usado_em
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS se ON se.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND a.name = 'annual_aggregation'
ORDER BY u.used_at;


-- ------------------------------------------------------------
-- Etapa 18 — Validação: annual_aggregation com 12 entradas
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Contagem de prov_used na agregação anual.
--
-- Por que isso importa:
-- Invariante do demo: exatamente 12 meses.
--
-- Como interpretar:
-- Coluna entradas_mensais deve ser 12.
SELECT
    COUNT(u.used_id) AS entradas_mensais
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND a.name = 'annual_aggregation';


-- ------------------------------------------------------------
-- Etapa 19 — Entidade annual_aggregate
-- ------------------------------------------------------------
-- O que esta query mostra:
-- prov_entity entity_kind annual-aggregation.
--
-- Por que isso importa:
-- Produto da agregação; insumo lógico do cálculo anual.
--
-- Como interpretar:
-- Uma entidade no run anual.
SELECT
    e.entity_id AS id_entidade,
    e.entity_kind AS kind_entidade,
    e.name AS nome_entidade,
    e.content_hash AS hash_entidade
FROM prov_core_prov_entity AS e
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = e.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND e.entity_kind = 'annual-aggregation';


-- ------------------------------------------------------------
-- Etapa 20 — PROV: annual_aggregate gerado pela agregação (generated)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- generated annual_aggregation → annual_aggregate.
--
-- Por que isso importa:
-- Saída formal da atividade de agregação.
--
-- Como interpretar:
-- Uma linha.
SELECT
    e.name AS entidade_agregada,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND a.name = 'annual_aggregation';


-- ------------------------------------------------------------
-- Etapa 21 — PROV: annual_aggregate deriva dos 12 meses (derived_from)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- derived_from mensal → agregado anual.
--
-- Por que isso importa:
-- Linhagem rollup explícita em PROV.
--
-- Como interpretar:
-- 12 linhas derivation_type annual_aggregation.
SELECT
    se.name AS fonte_mensal,
    ge.name AS agregado_anual,
    d.derivation_type AS tipo_derivacao
FROM prov_core_prov_derived_from AS d
INNER JOIN prov_core_prov_entity AS ge ON ge.entity_id = d.generated_entity_id
INNER JOIN prov_core_prov_entity AS se ON se.entity_id = d.source_entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ge.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND d.derivation_type = 'annual_aggregation'
ORDER BY se.name;


-- ------------------------------------------------------------
-- Etapa 22 — Métrica de negócio: produção agregada (validação)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_result_item aggregated_milk_production no run anual.
--
-- Por que isso importa:
-- Validação quantitativa esperada (~150500 L no demo).
--
-- Como interpretar:
-- Uma linha com result_value e result_unit.
SELECT
    ri.result_name AS nome_metrica,
    ri.result_value AS valor,
    ri.result_unit AS unidade
FROM calculation_calculation_result_item AS ri
INNER JOIN calculation_calculation_result_set AS rs
    ON rs.calculation_result_set_id = ri.calculation_result_set_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND ri.result_name = 'aggregated_milk_production';


-- ============================================================
-- 6. CÁLCULO E RESULTADO PRELIMINAR
-- ============================================================

-- ------------------------------------------------------------
-- Etapa C1 — Método e versão de cálculo
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_method e calculation_method_version do catálogo demo.
--
-- Por que isso importa:
-- Define metodologia GHG e versão aplicada.
--
-- Como interpretar:
-- method_code demo-repo-ghg-2026; version_label 1.0.0; status active.
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
-- Etapa C2 — Conjunto e valores de parâmetros
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_parameter_set e parameter_value do run.
--
-- Por que isso importa:
-- Parâmetros documentam premissas do cálculo.
--
-- Como interpretar:
-- parameter_set_status locked/approved após setup do demo.
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
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual';

-- ------------------------------------------------------------
-- Etapa C3 — Execução do cálculo
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_execution ligando método, parâmetros e canonical_snapshot.
--
-- Por que isso importa:
-- Registra a atividade de cálculo sobre a base canônica do run.
--
-- Como interpretar:
-- Uma execução por run de cálculo; canonical_snapshot_id aponta ao snapshot de entrada.
SELECT
    ce.calculation_execution_id AS id_execucao_calculo,
    ce.execution_status AS status_calculo,
    ce.started_at AS inicio_calculo,
    ce.finished_at AS fim_calculo,
    ce.canonical_snapshot_id AS id_snapshot_entrada,
    ce.prov_activity_id AS id_atividade_prov_calculo
FROM calculation_calculation_execution AS ce
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ce.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual';

-- ------------------------------------------------------------
-- Etapa C4 — PROV: cálculo usou snapshot canônico (used)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Entidade consumida pela atividade calculation_execution.
--
-- Por que isso importa:
-- Evidência PROV do insumo do cálculo (snapshot canônico ou agregado).
--
-- Como interpretar:
-- Uma linha principal; entity_type canonical_snapshot ou entidade de agregação.
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
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND a.activity_type = 'calculation_execution';

-- ------------------------------------------------------------
-- Etapa C5 — Result set preliminar
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_result_set gerado (status evolui após revisão).
--
-- Por que isso importa:
-- Armazena resultado quantitativo antes da aprovação.
--
-- Como interpretar:
-- result_set_status preliminary até review; depois approved.
SELECT
    rs.calculation_result_set_id AS id_conjunto_resultado,
    rs.result_set_status AS status_resultado,
    rs.generated_at AS gerado_em,
    rs.summary_hash AS hash_resumo
FROM calculation_calculation_result_set AS rs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual';

-- ------------------------------------------------------------
-- Etapa C6 — Itens de resultado (métricas)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_result_item com valores de negócio.
--
-- Por que isso importa:
-- Métricas finais auditáveis (ex.: produção de leite).
--
-- Como interpretar:
-- result_name e result_unit conforme método demo.
SELECT
    ri.result_name AS nome_metrica,
    ri.result_type AS tipo_resultado,
    ri.result_value AS valor,
    ri.result_unit AS unidade
FROM calculation_calculation_result_item AS ri
INNER JOIN calculation_calculation_result_set AS rs
    ON rs.calculation_result_set_id = ri.calculation_result_set_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual';

-- ------------------------------------------------------------
-- Etapa C7 — PROV: resultado gerado pelo cálculo (generated)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Relação generated calculation_execution → result_set.
--
-- Por que isso importa:
-- Formaliza produção do resultado preliminar.
--
-- Como interpretar:
-- Uma linha ligando atividade de cálculo ao result_set.
SELECT
    g.generated_id AS id_generated,
    a.name AS atividade_calculo,
    e.name AS entidade_resultado,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND a.activity_type = 'calculation_execution';

-- ============================================================
-- 7. APROVAÇÃO HUMANA E PUBLICAÇÃO FINAL
-- ============================================================

-- ------------------------------------------------------------
-- Etapa C8 — Revisão humana (aprovação)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- calculation_review com decisão e revisor.
--
-- Por que isso importa:
-- Gate de governança antes da publicação.
--
-- Como interpretar:
-- decision = approved; nome_revisor do agente humano demo.
SELECT
    cr.calculation_review_id AS id_revisao,
    cr.decision AS decisao_revisor,
    cr.review_comment AS comentario_revisao,
    cr.reviewed_at AS revisado_em,
    ag.name AS nome_revisor
FROM calculation_calculation_review AS cr
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cr.pipeline_run_id
LEFT JOIN prov_core_prov_agent AS ag ON ag.agent_id = cr.reviewer_agent_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual';

-- ------------------------------------------------------------
-- Etapa C9 — PROV: revisão usou resultado (used)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- used da calculation_review sobre result_set.
--
-- Por que isso importa:
-- Liga formalmente revisão ao artefato revisado.
--
-- Como interpretar:
-- role reviewed_result_set ou equivalente.
SELECT
    e.name AS resultado_revisado,
    u.role AS papel
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND a.activity_type = 'calculation_review';

-- ------------------------------------------------------------
-- Etapa C10 — PROV: agente associado à revisão (associated_with)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- associated_with entre revisão e agente revisor.
--
-- Por que isso importa:
-- Atribui responsabilidade humana à aprovação.
--
-- Como interpretar:
-- papel reviewer no demo.
SELECT
    ag.name AS agente_revisor,
    aw.role AS papel_agente
FROM prov_core_prov_associated_with AS aw
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = aw.activity_id
INNER JOIN prov_core_prov_agent AS ag ON ag.agent_id = aw.agent_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND a.activity_type = 'calculation_review';

-- ------------------------------------------------------------
-- Etapa C11 — Publicação final do resultado aprovado
-- ------------------------------------------------------------
-- O que esta query mostra:
-- result_publication_execution na ontologia de destino.
--
-- Por que isso importa:
-- Última etapa funcional antes de hash/anchor.
--
-- Como interpretar:
-- publication_status published; calculation_review_id preenchido.
SELECT
    pe.result_publication_execution_id AS id_publicacao,
    pe.publication_status AS status_publicacao,
    pe.published_at AS publicado_em,
    pe.target_graph_name AS grafo_destino,
    pe.calculation_review_id AS id_revisao_vinculada
FROM calculation_result_publication_execution AS pe
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = pe.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual';

-- ------------------------------------------------------------
-- Etapa C12 — Link ontológico da publicação final (se gerado)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- ontology_resource_link no estágio publication_final.
--
-- Por que isso importa:
-- Demonstra publicação do resultado no grafo ontológico.
--
-- Como interpretar:
-- 0 ou 1 linha; se vazio, publicação ainda existe em result_publication_execution.
SELECT
    orl.ontology_resource_link_id AS id_link,
    orl.ontology_uri AS uri_ontologia,
    orl.publication_stage AS estagio,
    orl.published_at AS publicado_em
FROM semantic_ontology_resource_link AS orl
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = orl.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
  AND orl.publication_stage IN ('publication_final', 'final');

-- ============================================================
-- 8. HASHES E BLOCKCHAIN SIMULADO
-- ============================================================

-- ------------------------------------------------------------
-- Etapa C13 — Registros de hash (integridade)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- audit_hash_record por subject_kind.
--
-- Por que isso importa:
-- Suporte à verificação de integridade e ancoragem.
--
-- Como interpretar:
-- Várias linhas: canonical_snapshot, calculation_result_set, source_artifact, etc.
SELECT
    hr.hash_record_id AS id_hash,
    hr.subject_kind AS tipo_sujeito,
    hr.subject_id AS id_sujeito,
    hr.hash_algorithm AS algoritmo,
    hr.hash_value AS valor_hash,
    hr.computed_at AS calculado_em
FROM audit_hash_record AS hr
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = hr.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
ORDER BY hr.subject_kind, hr.computed_at;

-- ------------------------------------------------------------
-- Etapa C14 — Ancoragem blockchain simulada
-- ------------------------------------------------------------
-- O que esta query mostra:
-- audit_blockchain_anchor ligado a hash_record.
--
-- Por que isso importa:
-- Simula compromisso externo (demo-chain).
--
-- Como interpretar:
-- anchor_status confirmed; transaction_hash prefixado demo-tx-.
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
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual';

-- ------------------------------------------------------------
-- Etapa C15 — Eventos de auditoria complementares
-- ------------------------------------------------------------
-- O que esta query mostra:
-- audit_audit_event do demo.
--
-- Por que isso importa:
-- Trilha adicional ao ledger operacional.
--
-- Como interpretar:
-- event_type demo.* ou calculation_review.*.
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
-- Etapa C16 — Eventos de outbox (integração assíncrona)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- audit_outbox_event emitidos durante gravações.
--
-- Por que isso importa:
-- Mostra eventos de domínio para relay/downstream.
--
-- Como interpretar:
-- Filtrar mentalmente por aggregate_kind do run se necessário.
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
-- Etapa P1 — Todas as relações used do caso (Boa Vista)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Visão consolidada de prov_core_prov_used.
--
-- Por que isso importa:
-- Mapa de consumo: wrapper, semântica, agregação (se houver), cálculo, revisão, publicação.
--
-- Como interpretar:
-- Ordene por run_code e atividade_nome para narrar a apresentação.
SELECT
    u.used_id AS id_used,
    r.run_code AS codigo_execucao,
    a.activity_type AS tipo_atividade,
    a.name AS atividade_nome,
    u.role AS papel,
    e.entity_type AS tipo_entidade,
    e.entity_kind AS kind_entidade,
    e.name AS entidade_nome,
    u.used_at AS usado_em
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_boa_vista_2026%'
ORDER BY r.run_code, a.name, u.used_at;

-- ------------------------------------------------------------
-- Etapa P2 — Todas as relações generated do caso (Boa Vista)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Visão consolidada de prov_core_prov_generated.
--
-- Por que isso importa:
-- Mostra o que cada atividade produziu formalmente em PROV.
--
-- Como interpretar:
-- Pares atividade_nome + entidade_nome devem fechar cada etapa da pipeline.
SELECT
    g.generated_id AS id_generated,
    r.run_code AS codigo_execucao,
    a.activity_type AS tipo_atividade,
    a.name AS atividade_nome,
    e.entity_type AS tipo_entidade,
    e.entity_kind AS kind_entidade,
    e.name AS entidade_nome,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_boa_vista_2026%'
ORDER BY r.run_code, g.generated_at;

-- ------------------------------------------------------------
-- Etapa P3 — Todas as relações derived_from do caso (Boa Vista)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Derivações explícitas entre entidades (rollup, transformação).
--
-- Por que isso importa:
-- Prova linhagem formal entre entidade fonte e entidade derivada.
--
-- Como interpretar:
-- No caso anual direto pode haver poucas linhas; no mensal→anual espere 12 derived_from da agregação.
SELECT
    d.derived_id AS id_derivacao,
    r.run_code AS codigo_execucao,
    d.derivation_type AS tipo_derivacao,
    ge.name AS entidade_gerada,
    ge.entity_kind AS kind_gerada,
    se.name AS entidade_fonte,
    se.entity_kind AS kind_fonte
FROM prov_core_prov_derived_from AS d
INNER JOIN prov_core_prov_entity AS ge ON ge.entity_id = d.generated_entity_id
INNER JOIN prov_core_prov_entity AS se ON se.entity_id = d.source_entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ge.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_boa_vista_2026%'
ORDER BY r.run_code, d.derivation_type, se.name;

-- ------------------------------------------------------------
-- Etapa P4 — Todas as relações associated_with do caso (Boa Vista)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Vínculos atividade ↔ agente (ex.: revisor humano).
--
-- Por que isso importa:
-- Atribui responsabilidade humana a atividades de revisão.
--
-- Como interpretar:
-- Pelo menos uma linha na calculation_review com papel reviewer.
SELECT
    aw.association_id AS id_associacao,
    r.run_code AS codigo_execucao,
    a.name AS atividade_nome,
    a.activity_type AS tipo_atividade,
    ag.name AS agente_nome,
    ag.agent_type AS tipo_agente,
    aw.role AS papel
FROM prov_core_prov_associated_with AS aw
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = aw.activity_id
INNER JOIN prov_core_prov_agent AS ag ON ag.agent_id = aw.agent_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_boa_vista_2026%'
ORDER BY r.run_code, a.name;

-- ------------------------------------------------------------
-- Etapa P5 — Relações revision do caso (Boa Vista)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Revisões PROV entre entidades (reprocessamento).
--
-- Por que isso importa:
-- Documenta substituição formal de entidades após reprocessamento.
--
-- Como interpretar:
-- Zero linhas é normal nestes casos; revisão formal está no demo de reprocessamento (outro run_code).
SELECT
    pr.revision_id AS id_revisao,
    pr.revision_reason AS motivo,
    pr.revised_at AS revisado_em,
    pe.name AS entidade_anterior,
    ne.name AS entidade_nova
FROM prov_core_prov_revision AS pr
INNER JOIN prov_core_prov_entity AS pe ON pe.entity_id = pr.previous_entity_id
INNER JOIN prov_core_prov_entity AS ne ON ne.entity_id = pr.new_entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ne.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_boa_vista_2026%'
ORDER BY pr.revised_at;

-- ------------------------------------------------------------
-- Etapa P6 — Resumo tabular do grafo PROV (Boa Vista)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- UNION de used, generated e derived_from em formato único para slides.
--
-- Por que isso importa:
-- Consolida o grafo para apresentação sem navegar tabela a tabela.
--
-- Como interpretar:
-- tipo_relacao distingue o papel de cada linha no grafo.
SELECT
    r.run_code AS codigo_execucao,
    a.name AS atividade,
    a.activity_type AS tipo_atividade,
    u.role AS relacao,
    'used' AS tipo_relacao,
    se.name AS entidade_entrada,
    CAST(NULL AS TEXT) AS entidade_saida
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS se ON se.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_boa_vista_2026%'
UNION ALL
SELECT
    r.run_code,
    a.name,
    a.activity_type,
    CAST(NULL AS TEXT),
    'generated',
    CAST(NULL AS TEXT),
    ge.name
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS ge ON ge.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_boa_vista_2026%'
UNION ALL
SELECT
    r.run_code,
    CAST(NULL AS TEXT),
    CAST(NULL AS TEXT),
    d.derivation_type,
    'derived_from',
    se.name,
    ge.name
FROM prov_core_prov_derived_from AS d
INNER JOIN prov_core_prov_entity AS ge ON ge.entity_id = d.generated_entity_id
INNER JOIN prov_core_prov_entity AS se ON se.entity_id = d.source_entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ge.pipeline_run_id
WHERE r.run_code LIKE 'demo_repo_boa_vista_2026%'
ORDER BY codigo_execucao, tipo_relacao, atividade;


-- ============================================================
-- 10. LINHAGEM COMPLETA DO CASO
-- ============================================================


-- ------------------------------------------------------------
-- Etapa — — Contagens por fase da pipeline
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Resumo quantitativo: mensais, agregação, publicação.
--
-- Por que isso importa:
-- Slide de fechamento com números-chave.
--
-- Como interpretar:
-- mensal=12; entradas_agregacao=12; publicacao_anual=1.
SELECT 'runs_mensais' AS fase, COUNT(*) AS quantidade
FROM pipeline_pipeline_run AS r
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
UNION ALL
SELECT 'atividade_annual_aggregation', COUNT(*)
FROM prov_core_prov_activity AS a
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual' AND a.name = 'annual_aggregation'
UNION ALL
SELECT 'entradas_na_agregacao', COUNT(*)
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual' AND a.name = 'annual_aggregation'
UNION ALL
SELECT 'publicacao_anual', COUNT(*)
FROM calculation_result_publication_execution AS pe
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = pe.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual';


-- ------------------------------------------------------------
-- Etapa — — Linhagem resumida mensal → anual (narrativa)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- UNION das etapas principais até hash no run anual.
--
-- Por que isso importa:
-- Narrativa ponta a ponta para banca.
--
-- Como interpretar:
-- ordem_etapa crescente; último passo blockchain no run anual.
SELECT
    1 AS ordem_etapa,
    '12_runs_mensais' AS etapa_pipeline,
    CAST(COUNT(*) AS TEXT) AS referencia,
    'monthly' AS periodo,
    'succeeded' AS status,
    'Bruto mensal por mês' AS observacao
FROM pipeline_pipeline_run AS r
WHERE r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
UNION ALL
SELECT 2, 'annual_aggregation', a.name, r.reporting_period_reference, a.status, 'Consolida 12 snapshots'
FROM prov_core_prov_activity AS a
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual' AND a.name = 'annual_aggregation'
UNION ALL
SELECT 3, 'annual_aggregate', e.name, r.reporting_period_reference, e.entity_kind, 'Entidade agregada'
FROM prov_core_prov_entity AS e
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = e.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual' AND e.entity_kind = 'annual-aggregation'
UNION ALL
SELECT 4, 'calculation_execution', ce.calculation_execution_id, r.reporting_period_reference, ce.execution_status, 'Cálculo sobre agregado'
FROM calculation_calculation_execution AS ce
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ce.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
UNION ALL
SELECT 5, 'result_set', rs.calculation_result_set_id, r.reporting_period_reference, rs.result_set_status, 'Resultado e governança'
FROM calculation_calculation_result_set AS rs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
UNION ALL
SELECT 6, 'blockchain_anchor', ba.blockchain_anchor_id, r.reporting_period_reference, ba.anchor_status, ba.transaction_hash
FROM audit_blockchain_anchor AS ba
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ba.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual'
ORDER BY ordem_etapa;


-- ------------------------------------------------------------
-- Etapa — — Verificação: cálculo no run anual (não 12 cálculos mensais)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Contagem de calculation_execution no run anual.
--
-- Por que isso importa:
-- O total anual vem de um cálculo sobre o agregado.
--
-- Como interpretar:
-- execucoes_calculo_run_anual = 1.
SELECT
    COUNT(*) AS execucoes_calculo_run_anual
FROM calculation_calculation_execution AS ce
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ce.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual';


-- ------------------------------------------------------------
-- Etapa — — Cadeia operacional do run anual (join spine)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Join das tabelas críticas no run anual de consolidação.
--
-- Por que isso importa:
-- Visão técnica pós-agregação.
--
-- Como interpretar:
-- Uma linha com snapshot, cálculo, resultado, revisão e publicação.
SELECT
    r.run_code AS codigo_execucao,
    cs.snapshot_label AS snapshot_entrada_calculo,
    ce.calculation_execution_id AS id_calculo,
    rs.result_set_status AS status_resultado,
    cr.decision AS decisao_revisao,
    pe.publication_status AS status_publicacao
FROM pipeline_pipeline_run AS r
LEFT JOIN semantic_canonical_snapshot AS cs ON cs.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_calculation_execution AS ce ON ce.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_calculation_result_set AS rs ON rs.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_calculation_review AS cr ON cr.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_result_publication_execution AS pe ON pe.pipeline_run_id = r.pipeline_run_id
WHERE r.run_code = 'demo_repo_boa_vista_2026-annual';
