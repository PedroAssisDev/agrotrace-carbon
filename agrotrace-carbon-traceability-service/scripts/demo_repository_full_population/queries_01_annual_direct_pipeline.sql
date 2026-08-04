-- ============================================================
-- CASO 1: FAZENDA SÃO PEDRO — DADO ANUAL DIRETO
-- ============================================================
--
-- Objetivo:
-- Apresentar, query a query, a proveniência registrada no SQLite para este cenário
-- de demonstração, na ordem do fluxo oficial da pipeline.
--
-- Fazenda / personagem: Fazenda São Pedro
-- Granularidade: annual (anual direto, sem agregação prévia)
--
-- Fluxo da pipeline (ordem deste arquivo):
--   1. Identificação da execução
--   2. Entrada de dados brutos
--   3. Wrapper e normalização
--   4. Integração semântica e ontologia
--   5. Agregação (verificação de ausência)
--   6. Cálculo e resultado preliminar
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
--   sqlite3 data/provenance.db < scripts/demo_repository_full_population/queries_01_annual_direct_pipeline.sql
--
-- Filtros de referência (demo):
--   Run único: demo_repo_sao_pedro_2026
--   Sem monthly_aggregation nem annual_aggregation


-- ============================================================
-- 1. IDENTIFICAÇÃO DA EXECUÇÃO DA PIPELINE
-- ============================================================


-- ------------------------------------------------------------
-- Etapa 1 — Pipeline run do caso (raiz da linhagem)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- O pipeline_run principal (demo_repo_sao_pedro_2026) com período e status.
--
-- Por que isso importa:
-- Única execução operacional; ancora bundles e entidades PROV.
--
-- Como interpretar:
-- Uma linha; run_status succeeded; parent_pipeline_run_id nulo.
SELECT
    r.pipeline_run_id AS id_execucao_pipeline,
    r.run_code AS codigo_execucao,
    r.farm_reference AS fazenda,
    r.reporting_period_reference AS periodo_referencia,
    r.run_status AS status_execucao,
    r.started_at AS inicio_execucao,
    r.idempotency_key AS chave_idempotencia
FROM pipeline_pipeline_run AS r
WHERE r.run_code = 'demo_repo_sao_pedro_2026';


-- ------------------------------------------------------------
-- Etapa 2 — Bundles de proveniência por fase
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Bundles PROV (wrapper, semantic, calculation, publication).
--
-- Por que isso importa:
-- Organiza o grafo W3C PROV por etapa da pipeline.
--
-- Como interpretar:
-- Vários bundle_type no mesmo run_code.
SELECT
    b.bundle_type AS tipo_bundle,
    b.status AS status_bundle,
    b.name AS nome_bundle,
    b.created_at AS criado_em
FROM prov_core_prov_bundle AS b
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = b.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
ORDER BY b.bundle_type;


-- ------------------------------------------------------------
-- Etapa 3 — Agentes envolvidos (disparo e revisão)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Agentes software/humano que disparam o run ou aprovam resultado.
--
-- Por que isso importa:
-- Atribui responsabilidade operacional e de governança.
--
-- Como interpretar:
-- Inclui triggered_by do run e reviewer da calculation_review.
SELECT DISTINCT
    ag.agent_id AS id_agente,
    ag.agent_type AS tipo_agente,
    ag.name AS nome_agente,
    ag.external_reference AS referencia_externa
FROM prov_core_prov_agent AS ag
WHERE ag.agent_id IN (
    SELECT r.triggered_by_agent_id
    FROM pipeline_pipeline_run AS r
    WHERE r.run_code = 'demo_repo_sao_pedro_2026'
    UNION
    SELECT cr.reviewer_agent_id
    FROM calculation_calculation_review AS cr
    INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cr.pipeline_run_id
    WHERE r.run_code = 'demo_repo_sao_pedro_2026'
);


-- ============================================================
-- 2. ENTRADA DE DADOS BRUTOS
-- ============================================================


-- ------------------------------------------------------------
-- Etapa 4 — Artefato bruto anual (source_artifact)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Único arquivo/dado bruto anual de entrada.
--
-- Por que isso importa:
-- Primeiro registro material da cadeia; base para wrapper e hashes.
--
-- Como interpretar:
-- Uma linha; content_hash para integridade; prov_entity_id espelha entidade PROV.
SELECT
    sa.source_artifact_id AS id_artefato_bruto,
    sa.original_filename AS arquivo_original,
    sa.source_system AS sistema_origem,
    sa.storage_uri AS uri_armazenamento,
    sa.content_hash AS hash_conteudo,
    sa.received_at AS recebido_em,
    sa.prov_entity_id AS id_entidade_prov_bruto
FROM pipeline_source_artifact AS sa
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sa.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026';


-- ============================================================
-- 3. WRAPPER E NORMALIZAÇÃO
-- ============================================================


-- ------------------------------------------------------------
-- Etapa 5 — Definição de wrapper utilizada
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Catálogo wrapper_definition referenciado pela execução.
--
-- Por que isso importa:
-- Documenta transformação layout→normalizado para reprodutibilidade.
--
-- Como interpretar:
-- demo-repo-normalizer; se vazio, run_all não foi executado.
SELECT
    wd.wrapper_definition_id AS id_definicao_wrapper,
    wd.wrapper_name AS nome_wrapper,
    wd.wrapper_version AS versao_wrapper,
    wd.source_layout_name AS layout_fonte,
    wd.code_hash AS hash_codigo_wrapper
FROM pipeline_wrapper_definition AS wd
WHERE wd.wrapper_name = 'demo-repo-normalizer';


-- ------------------------------------------------------------
-- Etapa 6 — Execução de wrapper sobre o bruto anual
-- ------------------------------------------------------------
-- O que esta query mostra:
-- wrapper_execution ligada ao artefato de entrada.
--
-- Por que isso importa:
-- Segunda etapa operacional: bruto → lote normalizado.
--
-- Como interpretar:
-- execution_status succeeded; input_artifact_id aponta ao bruto.
SELECT
    we.wrapper_execution_id AS id_execucao_wrapper,
    we.execution_status AS status_wrapper,
    we.started_at AS inicio_wrapper,
    we.finished_at AS fim_wrapper,
    we.input_artifact_id AS id_artefato_entrada,
    we.prov_activity_id AS id_atividade_prov_wrapper
FROM pipeline_wrapper_execution AS we
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = we.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026';


-- ------------------------------------------------------------
-- Etapa 7 — Lote normalizado anual
-- ------------------------------------------------------------
-- O que esta query mostra:
-- normalized_batch produzido pelo wrapper.
--
-- Por que isso importa:
-- Insumo da integração semântica.
--
-- Como interpretar:
-- Uma linha; batch_code e content_hash auditáveis.
SELECT
    nb.normalized_batch_id AS id_lote_normalizado,
    nb.batch_code AS codigo_lote,
    nb.schema_version AS versao_schema,
    nb.record_count AS quantidade_registros,
    nb.content_hash AS hash_lote,
    nb.generated_at AS gerado_em,
    nb.prov_entity_id AS id_entidade_prov_lote
FROM pipeline_normalized_batch AS nb
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = nb.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026';


-- ------------------------------------------------------------
-- Etapa 8 — PROV: wrapper consumiu bruto (used)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- prov_core_prov_used wrapper → source_artifact.
--
-- Por que isso importa:
-- Formaliza consumo explícito do bruto.
--
-- Como interpretar:
-- Uma linha; role indica papel do insumo.
SELECT
    a.name AS nome_atividade,
    e.name AS entidade_consumida,
    e.entity_type AS tipo_entidade,
    u.role AS papel_uso,
    u.used_at AS usado_em
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
  AND a.activity_type = 'wrapper_execution';


-- ------------------------------------------------------------
-- Etapa 9 — PROV: wrapper gerou lote normalizado (generated)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- prov_core_prov_generated wrapper → normalized_batch.
--
-- Por que isso importa:
-- Formaliza produção do lote normalizado.
--
-- Como interpretar:
-- Uma linha; entidade_gerada é o lote do mesmo run.
SELECT
    a.name AS nome_atividade,
    e.name AS entidade_gerada,
    e.entity_type AS tipo_entidade,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
  AND a.activity_type = 'wrapper_execution';


-- ============================================================
-- 4. INTEGRAÇÃO SEMÂNTICA E ONTOLOGIA
-- ============================================================


-- ------------------------------------------------------------
-- Etapa 10 — Integração semântica sobre o lote normalizado
-- ------------------------------------------------------------
-- O que esta query mostra:
-- semantic_integration_execution com ontologia e status.
--
-- Por que isso importa:
-- Mapeia lote tabular para modelo canônico/ontológico.
--
-- Como interpretar:
-- Uma execução; normalized_batch_id = lote do run.
SELECT
    sie.semantic_integration_execution_id AS id_integracao_semantica,
    sie.ontology_name AS ontologia,
    sie.ontology_version AS versao_ontologia,
    sie.execution_status AS status_integracao,
    sie.started_at AS inicio_integracao,
    sie.normalized_batch_id AS id_lote_entrada,
    sie.prov_activity_id AS id_atividade_prov_semantica
FROM semantic_semantic_integration_execution AS sie
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sie.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026';


-- ------------------------------------------------------------
-- Etapa 11 — Snapshot canônico anual
-- ------------------------------------------------------------
-- O que esta query mostra:
-- canonical_snapshot usado como base do cálculo.
--
-- Por que isso importa:
-- Base semântica estável para o método GHG.
--
-- Como interpretar:
-- Uma linha; snapshot_hash para integridade.
SELECT
    cs.canonical_snapshot_id AS id_snapshot,
    cs.snapshot_label AS rotulo_snapshot,
    cs.graph_name AS nome_grafo,
    cs.snapshot_hash AS hash_snapshot,
    cs.published_at AS publicado_em,
    cs.prov_entity_id AS id_entidade_prov_snapshot
FROM semantic_canonical_snapshot AS cs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026';


-- ------------------------------------------------------------
-- Etapa 12 — Itens do snapshot canônico
-- ------------------------------------------------------------
-- O que esta query mostra:
-- canonical_snapshot_item com métricas atômicas.
--
-- Por que isso importa:
-- Detalha payload (ex.: produção de leite no período anual).
--
-- Como interpretar:
-- Pode haver várias linhas por item_key; depende do demo.
SELECT
    csi.canonical_snapshot_item_id AS id_item,
    csi.item_key AS chave_item,
    csi.item_hash AS hash_item,
    csi.payload AS conteudo_json
FROM semantic_canonical_snapshot_item AS csi
WHERE csi.canonical_snapshot_id IN (
    SELECT cs.canonical_snapshot_id
    FROM semantic_canonical_snapshot AS cs
    INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
    WHERE r.run_code = 'demo_repo_sao_pedro_2026'
);


-- ------------------------------------------------------------
-- Etapa 13 — Publicação canônica na ontologia (ontology resource link)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- ontology_resource_link do snapshot canônico.
--
-- Por que isso importa:
-- Vínculo do snapshot com recurso ontológico publicado.
--
-- Como interpretar:
-- publication_stage canônico; ontology_uri do demo.
SELECT
    orl.ontology_resource_link_id AS id_link,
    orl.ontology_uri AS uri_ontologia,
    orl.rdf_class AS classe_rdf,
    orl.graph_name AS nome_grafo,
    orl.publication_stage AS estagio_publicacao,
    orl.published_at AS publicado_em
FROM semantic_ontology_resource_link AS orl
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = orl.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026';


-- ------------------------------------------------------------
-- Etapa 14 — PROV: integração usou lote normalizado (used)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- used semantic_integration → normalized_batch.
--
-- Por que isso importa:
-- Amarra integração ao insumo correto.
--
-- Como interpretar:
-- Uma linha principal.
SELECT
    a.name AS nome_atividade,
    e.name AS entidade_consumida,
    e.entity_type AS tipo_entidade,
    u.used_at AS usado_em
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
  AND a.activity_type = 'semantic_integration';


-- ------------------------------------------------------------
-- Etapa 15 — PROV: integração gerou snapshot canônico (generated)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- generated semantic_integration → canonical_snapshot.
--
-- Por que isso importa:
-- Fecha etapa semântica com saída auditável.
--
-- Como interpretar:
-- Uma linha; entidade_gerada é o snapshot do run.
SELECT
    a.name AS nome_atividade,
    e.name AS entidade_gerada,
    e.entity_type AS tipo_entidade,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
  AND a.activity_type = 'semantic_integration';


-- ============================================================
-- 5. AGREGAÇÃO (VERIFICAÇÃO DE AUSÊNCIA NESTE CENÁRIO)
-- ============================================================


-- ------------------------------------------------------------
-- Etapa 16 — Verificação: sem monthly_aggregation
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Busca atividades monthly_aggregation no run.
--
-- Por que isso importa:
-- Cenário anual direto não possui rollup mensal.
--
-- Como interpretar:
-- Resultado esperado: zero linhas.
SELECT
    a.activity_id AS id_atividade,
    a.name AS nome_atividade
FROM prov_core_prov_activity AS a
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
  AND a.name LIKE '%monthly_aggregation%';


-- ------------------------------------------------------------
-- Etapa 17 — Verificação: sem annual_aggregation
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Busca atividade annual_aggregation no run.
--
-- Por que isso importa:
-- Dado já é anual; não há segunda agregação anual.
--
-- Como interpretar:
-- Resultado esperado: zero linhas.
SELECT
    a.activity_id AS id_atividade,
    a.name AS nome_atividade
FROM prov_core_prov_activity AS a
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
  AND a.name = 'annual_aggregation';


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
WHERE r.run_code = 'demo_repo_sao_pedro_2026';

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
WHERE r.run_code = 'demo_repo_sao_pedro_2026';

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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026';

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
WHERE r.run_code = 'demo_repo_sao_pedro_2026';

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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026';

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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026';

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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026';

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
-- Etapa P1 — Todas as relações used do caso (São Pedro)
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
ORDER BY r.run_code, a.name, u.used_at;

-- ------------------------------------------------------------
-- Etapa P2 — Todas as relações generated do caso (São Pedro)
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
ORDER BY r.run_code, g.generated_at;

-- ------------------------------------------------------------
-- Etapa P3 — Todas as relações derived_from do caso (São Pedro)
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
ORDER BY r.run_code, d.derivation_type, se.name;

-- ------------------------------------------------------------
-- Etapa P4 — Todas as relações associated_with do caso (São Pedro)
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
ORDER BY r.run_code, a.name;

-- ------------------------------------------------------------
-- Etapa P5 — Relações revision do caso (São Pedro)
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
ORDER BY pr.revised_at;

-- ------------------------------------------------------------
-- Etapa P6 — Resumo tabular do grafo PROV (São Pedro)
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
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
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
ORDER BY codigo_execucao, tipo_relacao, atividade;


-- ============================================================
-- 10. LINHAGEM COMPLETA DO CASO
-- ============================================================


-- ------------------------------------------------------------
-- Etapa — — Linhagem resumida ponta a ponta (narrativa)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- UNION ordenado das principais etapas do caso anual direto.
--
-- Por que isso importa:
-- Fechamento da apresentação em uma consulta.
--
-- Como interpretar:
-- ordem_etapa 1..10 do pipeline_run ao blockchain_anchor.
SELECT
    1 AS ordem_etapa,
    'pipeline_run' AS etapa_pipeline,
    r.run_code AS codigo_execucao,
    r.reporting_period_reference AS periodo,
    r.run_status AS status,
    'Início da linhagem (anual direto)' AS observacao
FROM pipeline_pipeline_run AS r
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
UNION ALL
SELECT 2, 'source_artifact', sa.original_filename, r.reporting_period_reference, 'received', sa.content_hash
FROM pipeline_source_artifact AS sa
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sa.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
UNION ALL
SELECT 3, 'wrapper_execution', we.wrapper_execution_id, r.reporting_period_reference, we.execution_status, 'Bruto para lote normalizado'
FROM pipeline_wrapper_execution AS we
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = we.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
UNION ALL
SELECT 4, 'normalized_batch', nb.batch_code, r.reporting_period_reference, 'generated', nb.content_hash
FROM pipeline_normalized_batch AS nb
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = nb.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
UNION ALL
SELECT 5, 'semantic_integration', sie.semantic_integration_execution_id, r.reporting_period_reference, sie.execution_status, 'Mapeamento ontológico'
FROM semantic_semantic_integration_execution AS sie
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sie.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
UNION ALL
SELECT 6, 'canonical_snapshot', cs.snapshot_label, r.reporting_period_reference, 'published', cs.snapshot_hash
FROM semantic_canonical_snapshot AS cs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
UNION ALL
SELECT 7, 'calculation_execution', ce.calculation_execution_id, r.reporting_period_reference, ce.execution_status, 'Cálculo sobre snapshot anual'
FROM calculation_calculation_execution AS ce
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ce.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
UNION ALL
SELECT 8, 'result_set', rs.calculation_result_set_id, r.reporting_period_reference, rs.result_set_status, 'Resultado, revisão e publicação'
FROM calculation_calculation_result_set AS rs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
UNION ALL
SELECT 9, 'hash_record', hr.hash_record_id, r.reporting_period_reference, hr.subject_kind, hr.hash_value
FROM audit_hash_record AS hr
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = hr.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
UNION ALL
SELECT 10, 'blockchain_anchor', ba.blockchain_anchor_id, r.reporting_period_reference, ba.anchor_status, ba.transaction_hash
FROM audit_blockchain_anchor AS ba
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ba.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026'
ORDER BY ordem_etapa;


-- ------------------------------------------------------------
-- Etapa — — Cadeia operacional (join spine no run único)
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Join das tabelas críticas no mesmo pipeline_run.
--
-- Por que isso importa:
-- Visão técnica para auditoria cruzada de FKs.
--
-- Como interpretar:
-- Uma linha se o demo estiver completo.
SELECT
    r.run_code AS codigo_execucao,
    sa.original_filename AS arquivo_bruto,
    nb.batch_code AS lote_normalizado,
    cs.snapshot_label AS snapshot_canonico,
    ce.calculation_execution_id AS id_calculo,
    rs.result_set_status AS status_resultado,
    cr.decision AS decisao_revisao,
    pe.publication_status AS status_publicacao
FROM pipeline_pipeline_run AS r
LEFT JOIN pipeline_source_artifact AS sa ON sa.pipeline_run_id = r.pipeline_run_id
LEFT JOIN pipeline_normalized_batch AS nb ON nb.pipeline_run_id = r.pipeline_run_id
LEFT JOIN semantic_canonical_snapshot AS cs ON cs.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_calculation_execution AS ce ON ce.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_calculation_result_set AS rs ON rs.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_calculation_review AS cr ON cr.pipeline_run_id = r.pipeline_run_id
LEFT JOIN calculation_result_publication_execution AS pe ON pe.pipeline_run_id = r.pipeline_run_id
WHERE r.run_code = 'demo_repo_sao_pedro_2026';
