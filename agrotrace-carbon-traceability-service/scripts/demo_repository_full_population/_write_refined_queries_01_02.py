"""Gera queries_01 e queries_02 no padrão didático do Caso 3 (10 seções). Não altera queries_03."""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).parent


def section(title: str) -> str:
    return f"""
-- ============================================================
-- {title}
-- ============================================================
"""


def query(
    step: str,
    title: str,
    shows: str,
    why: str,
    interpret: str,
    sql: str,
) -> str:
    return f"""
-- ------------------------------------------------------------
-- Etapa {step} — {title}
-- ------------------------------------------------------------
-- O que esta query mostra:
-- {shows}
--
-- Por que isso importa:
-- {why}
--
-- Como interpretar:
-- {interpret}
{sql.strip()}
"""


def file_header(
    case_title: str,
    farm: str,
    granularity: str,
    flow_lines: list[str],
    filename: str,
    filters_note: str,
) -> str:
    flow = "\n".join(f"--   {i}. {line}" for i, line in enumerate(flow_lines, 1))
    return f"""-- ============================================================
-- {case_title}
-- ============================================================
--
-- Objetivo:
-- Apresentar, query a query, a proveniência registrada no SQLite para este cenário
-- de demonstração, na ordem do fluxo oficial da pipeline.
--
-- Fazenda / personagem: {farm}
-- Granularidade: {granularity}
--
-- Fluxo da pipeline (ordem deste arquivo):
{flow}
--
-- Observação:
-- Apenas consultas SELECT. Não há INSERT, UPDATE ou DELETE.
--
-- Pré-requisito:
--   python scripts/demo_repository_full_population/run_all.py
--
-- Execução sugerida:
--   sqlite3 data/provenance.db < scripts/demo_repository_full_population/{filename}
--
-- Filtros de referência (demo):
{filters_note}
"""


def prov_block(case_where: str, farm_label: str) -> str:
    parts = [section("9. RELAÇÕES FORMAIS DE PROVENIÊNCIA"), query(
    "P1",
    f"Todas as relações used do caso ({farm_label})",
    "Visão consolidada de prov_core_prov_used.",
    "Mapa de consumo: wrapper, semântica, agregação (se houver), cálculo, revisão, publicação.",
    "Ordene por run_code e atividade_nome para narrar a apresentação.",
    "SELECT\n"
    "    u.used_id AS id_used,\n"
    "    r.run_code AS codigo_execucao,\n"
    "    a.activity_type AS tipo_atividade,\n"
    "    a.name AS atividade_nome,\n"
    "    u.role AS papel,\n"
    "    e.entity_type AS tipo_entidade,\n"
    "    e.entity_kind AS kind_entidade,\n"
    "    e.name AS entidade_nome,\n"
    "    u.used_at AS usado_em\n"
    "FROM prov_core_prov_used AS u\n"
    "INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id\n"
    "INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id\n"
    "INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id\n"
    f"WHERE {case_where}\n"
    "ORDER BY r.run_code, a.name, u.used_at;",
    ), query(
    "P2",
    f"Todas as relações generated do caso ({farm_label})",
    "Visão consolidada de prov_core_prov_generated.",
    "Mostra o que cada atividade produziu formalmente em PROV.",
    "Pares atividade_nome + entidade_nome devem fechar cada etapa da pipeline.",
    "SELECT\n"
    "    g.generated_id AS id_generated,\n"
    "    r.run_code AS codigo_execucao,\n"
    "    a.activity_type AS tipo_atividade,\n"
    "    a.name AS atividade_nome,\n"
    "    e.entity_type AS tipo_entidade,\n"
    "    e.entity_kind AS kind_entidade,\n"
    "    e.name AS entidade_nome,\n"
    "    g.generated_at AS gerado_em\n"
    "FROM prov_core_prov_generated AS g\n"
    "INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id\n"
    "INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id\n"
    "INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id\n"
    f"WHERE {case_where}\n"
    "ORDER BY r.run_code, g.generated_at;",
    ), query(
    "P3",
    f"Todas as relações derived_from do caso ({farm_label})",
    "Derivações explícitas entre entidades (rollup, transformação).",
    "Prova linhagem formal entre entidade fonte e entidade derivada.",
    "No caso anual direto pode haver poucas linhas; no mensal→anual espere 12 derived_from da agregação.",
    "SELECT\n"
    "    d.derived_id AS id_derivacao,\n"
    "    r.run_code AS codigo_execucao,\n"
    "    d.derivation_type AS tipo_derivacao,\n"
    "    ge.name AS entidade_gerada,\n"
    "    ge.entity_kind AS kind_gerada,\n"
    "    se.name AS entidade_fonte,\n"
    "    se.entity_kind AS kind_fonte\n"
    "FROM prov_core_prov_derived_from AS d\n"
    "INNER JOIN prov_core_prov_entity AS ge ON ge.entity_id = d.generated_entity_id\n"
    "INNER JOIN prov_core_prov_entity AS se ON se.entity_id = d.source_entity_id\n"
    "INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ge.pipeline_run_id\n"
    f"WHERE {case_where}\n"
    "ORDER BY r.run_code, d.derivation_type, se.name;",
    ), query(
    "P4",
    f"Todas as relações associated_with do caso ({farm_label})",
    "Vínculos atividade ↔ agente (ex.: revisor humano).",
    "Atribui responsabilidade humana a atividades de revisão.",
    "Pelo menos uma linha na calculation_review com papel reviewer.",
    "SELECT\n"
    "    aw.association_id AS id_associacao,\n"
    "    r.run_code AS codigo_execucao,\n"
    "    a.name AS atividade_nome,\n"
    "    a.activity_type AS tipo_atividade,\n"
    "    ag.name AS agente_nome,\n"
    "    ag.agent_type AS tipo_agente,\n"
    "    aw.role AS papel\n"
    "FROM prov_core_prov_associated_with AS aw\n"
    "INNER JOIN prov_core_prov_activity AS a ON a.activity_id = aw.activity_id\n"
    "INNER JOIN prov_core_prov_agent AS ag ON ag.agent_id = aw.agent_id\n"
    "INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id\n"
    f"WHERE {case_where}\n"
    "ORDER BY r.run_code, a.name;",
    ), query(
    "P5",
    f"Relações revision do caso ({farm_label})",
    "Revisões PROV entre entidades (reprocessamento).",
    "Documenta substituição formal de entidades após reprocessamento.",
    "Zero linhas é normal nestes casos; revisão formal está no demo de reprocessamento (outro run_code).",
    "SELECT\n"
    "    pr.revision_id AS id_revisao,\n"
    "    pr.revision_reason AS motivo,\n"
    "    pr.revised_at AS revisado_em,\n"
    "    pe.name AS entidade_anterior,\n"
    "    ne.name AS entidade_nova\n"
    "FROM prov_core_prov_revision AS pr\n"
    "INNER JOIN prov_core_prov_entity AS pe ON pe.entity_id = pr.previous_entity_id\n"
    "INNER JOIN prov_core_prov_entity AS ne ON ne.entity_id = pr.new_entity_id\n"
    "INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ne.pipeline_run_id\n"
    f"WHERE {case_where}\n"
    "ORDER BY pr.revised_at;",
    ), query(
    "P6",
    f"Resumo tabular do grafo PROV ({farm_label})",
    "UNION de used, generated e derived_from em formato único para slides.",
    "Consolida o grafo para apresentação sem navegar tabela a tabela.",
    "tipo_relacao distingue o papel de cada linha no grafo.",
    "SELECT\n"
    "    r.run_code AS codigo_execucao,\n"
    "    a.name AS atividade,\n"
    "    a.activity_type AS tipo_atividade,\n"
    "    u.role AS relacao,\n"
    "    'used' AS tipo_relacao,\n"
    "    se.name AS entidade_entrada,\n"
    "    CAST(NULL AS TEXT) AS entidade_saida\n"
    "FROM prov_core_prov_used AS u\n"
    "INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id\n"
    "INNER JOIN prov_core_prov_entity AS se ON se.entity_id = u.entity_id\n"
    "INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id\n"
    f"WHERE {case_where}\n"
    "UNION ALL\n"
    "SELECT\n"
    "    r.run_code,\n"
    "    a.name,\n"
    "    a.activity_type,\n"
    "    CAST(NULL AS TEXT),\n"
    "    'generated',\n"
    "    CAST(NULL AS TEXT),\n"
    "    ge.name\n"
    "FROM prov_core_prov_generated AS g\n"
    "INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id\n"
    "INNER JOIN prov_core_prov_entity AS ge ON ge.entity_id = g.entity_id\n"
    "INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id\n"
    f"WHERE {case_where}\n"
    "UNION ALL\n"
    "SELECT\n"
    "    r.run_code,\n"
    "    CAST(NULL AS TEXT),\n"
    "    CAST(NULL AS TEXT),\n"
    "    d.derivation_type,\n"
    "    'derived_from',\n"
    "    se.name,\n"
    "    ge.name\n"
    "FROM prov_core_prov_derived_from AS d\n"
    "INNER JOIN prov_core_prov_entity AS ge ON ge.entity_id = d.generated_entity_id\n"
    "INNER JOIN prov_core_prov_entity AS se ON se.entity_id = d.source_entity_id\n"
    "INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ge.pipeline_run_id\n"
    f"WHERE {case_where}\n"
    "ORDER BY codigo_execucao, tipo_relacao, atividade;",
    )]
    return "".join(parts)


def calc_review_hash_blocks(run_filter: str) -> str:
    rf = run_filter

    def q(step: str, title: str, shows: str, why: str, interpret: str, sql: str) -> str:
        return query(step, title, shows, why, interpret, sql.replace("__RUN__", rf))

    parts = [
        section("6. CÁLCULO E RESULTADO PRELIMINAR"),
        q(
    "C1",
    "Método e versão de cálculo",
    "calculation_method e calculation_method_version do catálogo demo.",
    "Define metodologia GHG e versão aplicada.",
    "method_code demo-repo-ghg-2026; version_label 1.0.0; status active.",
    """SELECT
    cm.method_code AS codigo_metodo,
    cm.method_name AS nome_metodo,
    cmv.version_label AS versao_metodo,
    cmv.status AS status_versao
FROM calculation_calculation_method AS cm
INNER JOIN calculation_calculation_method_version AS cmv
    ON cmv.calculation_method_id = cm.calculation_method_id
WHERE cm.method_code = 'demo-repo-ghg-2026';""",
        ),
        q(
    "C2",
    "Conjunto e valores de parâmetros",
    "calculation_parameter_set e parameter_value do run.",
    "Parâmetros documentam premissas do cálculo.",
    "parameter_set_status locked/approved após setup do demo.",
    """SELECT
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
WHERE __RUN__;""",
        ),
        q(
    "C3",
    "Execução do cálculo",
    "calculation_execution ligando método, parâmetros e canonical_snapshot.",
    "Registra a atividade de cálculo sobre a base canônica do run.",
    "Uma execução por run de cálculo; canonical_snapshot_id aponta ao snapshot de entrada.",
    """SELECT
    ce.calculation_execution_id AS id_execucao_calculo,
    ce.execution_status AS status_calculo,
    ce.started_at AS inicio_calculo,
    ce.finished_at AS fim_calculo,
    ce.canonical_snapshot_id AS id_snapshot_entrada,
    ce.prov_activity_id AS id_atividade_prov_calculo
FROM calculation_calculation_execution AS ce
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ce.pipeline_run_id
WHERE __RUN__;""",
        ),
        q(
    "C4",
    "PROV: cálculo usou snapshot canônico (used)",
    "Entidade consumida pela atividade calculation_execution.",
    "Evidência PROV do insumo do cálculo (snapshot canônico ou agregado).",
    "Uma linha principal; entity_type canonical_snapshot ou entidade de agregação.",
    """SELECT
    e.entity_id AS id_entidade_usada,
    e.entity_type AS tipo_entidade,
    e.name AS nome_entidade,
    e.entity_kind AS kind_entidade,
    u.role AS papel
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE __RUN__
  AND a.activity_type = 'calculation_execution';""",
        ),
        q(
    "C5",
    "Result set preliminar",
    "calculation_result_set gerado (status evolui após revisão).",
    "Armazena resultado quantitativo antes da aprovação.",
    "result_set_status preliminary até review; depois approved.",
    """SELECT
    rs.calculation_result_set_id AS id_conjunto_resultado,
    rs.result_set_status AS status_resultado,
    rs.generated_at AS gerado_em,
    rs.summary_hash AS hash_resumo
FROM calculation_calculation_result_set AS rs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE __RUN__;""",
        ),
        q(
    "C6",
    "Itens de resultado (métricas)",
    "calculation_result_item com valores de negócio.",
    "Métricas finais auditáveis (ex.: produção de leite).",
    "result_name e result_unit conforme método demo.",
    """SELECT
    ri.result_name AS nome_metrica,
    ri.result_type AS tipo_resultado,
    ri.result_value AS valor,
    ri.result_unit AS unidade
FROM calculation_calculation_result_item AS ri
INNER JOIN calculation_calculation_result_set AS rs
    ON rs.calculation_result_set_id = ri.calculation_result_set_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE __RUN__;""",
        ),
        q(
    "C7",
    "PROV: resultado gerado pelo cálculo (generated)",
    "Relação generated calculation_execution → result_set.",
    "Formaliza produção do resultado preliminar.",
    "Uma linha ligando atividade de cálculo ao result_set.",
    """SELECT
    g.generated_id AS id_generated,
    a.name AS atividade_calculo,
    e.name AS entidade_resultado,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE __RUN__
  AND a.activity_type = 'calculation_execution';""",
        ),
        section("7. APROVAÇÃO HUMANA E PUBLICAÇÃO FINAL"),
        q(
    "C8",
    "Revisão humana (aprovação)",
    "calculation_review com decisão e revisor.",
    "Gate de governança antes da publicação.",
    "decision = approved; nome_revisor do agente humano demo.",
    """SELECT
    cr.calculation_review_id AS id_revisao,
    cr.decision AS decisao_revisor,
    cr.review_comment AS comentario_revisao,
    cr.reviewed_at AS revisado_em,
    ag.name AS nome_revisor
FROM calculation_calculation_review AS cr
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cr.pipeline_run_id
LEFT JOIN prov_core_prov_agent AS ag ON ag.agent_id = cr.reviewer_agent_id
WHERE __RUN__;""",
        ),
        q(
    "C9",
    "PROV: revisão usou resultado (used)",
    "used da calculation_review sobre result_set.",
    "Liga formalmente revisão ao artefato revisado.",
    "role reviewed_result_set ou equivalente.",
    """SELECT
    e.name AS resultado_revisado,
    u.role AS papel
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE __RUN__
  AND a.activity_type = 'calculation_review';""",
        ),
        q(
    "C10",
    "PROV: agente associado à revisão (associated_with)",
    "associated_with entre revisão e agente revisor.",
    "Atribui responsabilidade humana à aprovação.",
    "papel reviewer no demo.",
    """SELECT
    ag.name AS agente_revisor,
    aw.role AS papel_agente
FROM prov_core_prov_associated_with AS aw
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = aw.activity_id
INNER JOIN prov_core_prov_agent AS ag ON ag.agent_id = aw.agent_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE __RUN__
  AND a.activity_type = 'calculation_review';""",
        ),
        q(
    "C11",
    "Publicação final do resultado aprovado",
    "result_publication_execution na ontologia de destino.",
    "Última etapa funcional antes de hash/anchor.",
    "publication_status published; calculation_review_id preenchido.",
    """SELECT
    pe.result_publication_execution_id AS id_publicacao,
    pe.publication_status AS status_publicacao,
    pe.published_at AS publicado_em,
    pe.target_graph_name AS grafo_destino,
    pe.calculation_review_id AS id_revisao_vinculada
FROM calculation_result_publication_execution AS pe
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = pe.pipeline_run_id
WHERE __RUN__;""",
        ),
        q(
    "C12",
    "Link ontológico da publicação final (se gerado)",
    "ontology_resource_link no estágio publication_final.",
    "Demonstra publicação do resultado no grafo ontológico.",
    "0 ou 1 linha; se vazio, publicação ainda existe em result_publication_execution.",
    """SELECT
    orl.ontology_resource_link_id AS id_link,
    orl.ontology_uri AS uri_ontologia,
    orl.publication_stage AS estagio,
    orl.published_at AS publicado_em
FROM semantic_ontology_resource_link AS orl
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = orl.pipeline_run_id
WHERE __RUN__
  AND orl.publication_stage IN ('publication_final', 'final');""",
        ),
        section("8. HASHES E BLOCKCHAIN SIMULADO"),
        q(
    "C13",
    "Registros de hash (integridade)",
    "audit_hash_record por subject_kind.",
    "Suporte à verificação de integridade e ancoragem.",
    "Várias linhas: canonical_snapshot, calculation_result_set, source_artifact, etc.",
    """SELECT
    hr.hash_record_id AS id_hash,
    hr.subject_kind AS tipo_sujeito,
    hr.subject_id AS id_sujeito,
    hr.hash_algorithm AS algoritmo,
    hr.hash_value AS valor_hash,
    hr.computed_at AS calculado_em
FROM audit_hash_record AS hr
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = hr.pipeline_run_id
WHERE __RUN__
ORDER BY hr.subject_kind, hr.computed_at;""",
        ),
        q(
    "C14",
    "Ancoragem blockchain simulada",
    "audit_blockchain_anchor ligado a hash_record.",
    "Simula compromisso externo (demo-chain).",
    "anchor_status confirmed; transaction_hash prefixado demo-tx-.",
    """SELECT
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
WHERE __RUN__;""",
        ),
        q(
    "C15",
    "Eventos de auditoria complementares",
    "audit_audit_event do demo.",
    "Trilha adicional ao ledger operacional.",
    "event_type demo.* ou calculation_review.*.",
    """SELECT
    ae.audit_event_id AS id_evento,
    ae.event_type AS tipo_evento,
    ae.subject_kind AS tipo_sujeito,
    ae.recorded_at AS registrado_em
FROM audit_audit_event AS ae
WHERE ae.event_type LIKE 'demo.%'
   OR ae.event_type LIKE 'calculation_review.%'
ORDER BY ae.recorded_at DESC
LIMIT 20;""",
        ),
        q(
    "C16",
    "Eventos de outbox (integração assíncrona)",
    "audit_outbox_event emitidos durante gravações.",
    "Mostra eventos de domínio para relay/downstream.",
    "Filtrar mentalmente por aggregate_kind do run se necessário.",
    """SELECT
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
LIMIT 25;""",
        ),
    ]
    return "".join(parts)


def build_queries_01() -> str:
    run = "demo_repo_sao_pedro_2026"
    rf = f"r.run_code = '{run}'"
    cw = rf
    parts = [
        file_header(
            "CASO 1: FAZENDA SÃO PEDRO — DADO ANUAL DIRETO",
            "Fazenda São Pedro",
            "annual (anual direto, sem agregação prévia)",
            [
                "Identificação da execução",
                "Entrada de dados brutos",
                "Wrapper e normalização",
                "Integração semântica e ontologia",
                "Agregação (verificação de ausência)",
                "Cálculo e resultado preliminar",
                "Aprovação humana e publicação final",
                "Hashes e blockchain simulado",
                "Relações formais de proveniência",
                "Linhagem completa do caso",
            ],
            "queries_01_annual_direct_pipeline.sql",
            f"--   Run único: {run}\n--   Sem monthly_aggregation nem annual_aggregation",
        ),
        section("1. IDENTIFICAÇÃO DA EXECUÇÃO DA PIPELINE"),
        query(
            "1",
            "Pipeline run do caso (raiz da linhagem)",
            f"O pipeline_run principal ({run}) com período e status.",
            "Única execução operacional; ancora bundles e entidades PROV.",
            "Uma linha; run_status succeeded; parent_pipeline_run_id nulo.",
            f"""SELECT
    r.pipeline_run_id AS id_execucao_pipeline,
    r.run_code AS codigo_execucao,
    r.farm_reference AS fazenda,
    r.reporting_period_reference AS periodo_referencia,
    r.run_status AS status_execucao,
    r.started_at AS inicio_execucao,
    r.idempotency_key AS chave_idempotencia
FROM pipeline_pipeline_run AS r
WHERE {rf};""",
        ),
        query(
            "2",
            "Bundles de proveniência por fase",
            "Bundles PROV (wrapper, semantic, calculation, publication).",
            "Organiza o grafo W3C PROV por etapa da pipeline.",
            "Vários bundle_type no mesmo run_code.",
            f"""SELECT
    b.bundle_type AS tipo_bundle,
    b.status AS status_bundle,
    b.name AS nome_bundle,
    b.created_at AS criado_em
FROM prov_core_prov_bundle AS b
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = b.pipeline_run_id
WHERE {rf}
ORDER BY b.bundle_type;""",
        ),
        query(
            "3",
            "Agentes envolvidos (disparo e revisão)",
            "Agentes software/humano que disparam o run ou aprovam resultado.",
            "Atribui responsabilidade operacional e de governança.",
            "Inclui triggered_by do run e reviewer da calculation_review.",
            f"""SELECT DISTINCT
    ag.agent_id AS id_agente,
    ag.agent_type AS tipo_agente,
    ag.name AS nome_agente,
    ag.external_reference AS referencia_externa
FROM prov_core_prov_agent AS ag
WHERE ag.agent_id IN (
    SELECT r.triggered_by_agent_id
    FROM pipeline_pipeline_run AS r
    WHERE {rf}
    UNION
    SELECT cr.reviewer_agent_id
    FROM calculation_calculation_review AS cr
    INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cr.pipeline_run_id
    WHERE {rf}
);""",
        ),
        section("2. ENTRADA DE DADOS BRUTOS"),
        query(
            "4",
            "Artefato bruto anual (source_artifact)",
            "Único arquivo/dado bruto anual de entrada.",
            "Primeiro registro material da cadeia; base para wrapper e hashes.",
            "Uma linha; content_hash para integridade; prov_entity_id espelha entidade PROV.",
            f"""SELECT
    sa.source_artifact_id AS id_artefato_bruto,
    sa.original_filename AS arquivo_original,
    sa.source_system AS sistema_origem,
    sa.storage_uri AS uri_armazenamento,
    sa.content_hash AS hash_conteudo,
    sa.received_at AS recebido_em,
    sa.prov_entity_id AS id_entidade_prov_bruto
FROM pipeline_source_artifact AS sa
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sa.pipeline_run_id
WHERE {rf};""",
        ),
        section("3. WRAPPER E NORMALIZAÇÃO"),
        query(
            "5",
            "Definição de wrapper utilizada",
            "Catálogo wrapper_definition referenciado pela execução.",
            "Documenta transformação layout→normalizado para reprodutibilidade.",
            "demo-repo-normalizer; se vazio, run_all não foi executado.",
            """SELECT
    wd.wrapper_definition_id AS id_definicao_wrapper,
    wd.wrapper_name AS nome_wrapper,
    wd.wrapper_version AS versao_wrapper,
    wd.source_layout_name AS layout_fonte,
    wd.code_hash AS hash_codigo_wrapper
FROM pipeline_wrapper_definition AS wd
WHERE wd.wrapper_name = 'demo-repo-normalizer';""",
        ),
        query(
            "6",
            "Execução de wrapper sobre o bruto anual",
            "wrapper_execution ligada ao artefato de entrada.",
            "Segunda etapa operacional: bruto → lote normalizado.",
            "execution_status succeeded; input_artifact_id aponta ao bruto.",
            f"""SELECT
    we.wrapper_execution_id AS id_execucao_wrapper,
    we.execution_status AS status_wrapper,
    we.started_at AS inicio_wrapper,
    we.finished_at AS fim_wrapper,
    we.input_artifact_id AS id_artefato_entrada,
    we.prov_activity_id AS id_atividade_prov_wrapper
FROM pipeline_wrapper_execution AS we
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = we.pipeline_run_id
WHERE {rf};""",
        ),
        query(
            "7",
            "Lote normalizado anual",
            "normalized_batch produzido pelo wrapper.",
            "Insumo da integração semântica.",
            "Uma linha; batch_code e content_hash auditáveis.",
            f"""SELECT
    nb.normalized_batch_id AS id_lote_normalizado,
    nb.batch_code AS codigo_lote,
    nb.schema_version AS versao_schema,
    nb.record_count AS quantidade_registros,
    nb.content_hash AS hash_lote,
    nb.generated_at AS gerado_em,
    nb.prov_entity_id AS id_entidade_prov_lote
FROM pipeline_normalized_batch AS nb
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = nb.pipeline_run_id
WHERE {rf};""",
        ),
        query(
            "8",
            "PROV: wrapper consumiu bruto (used)",
            "prov_core_prov_used wrapper → source_artifact.",
            "Formaliza consumo explícito do bruto.",
            "Uma linha; role indica papel do insumo.",
            f"""SELECT
    a.name AS nome_atividade,
    e.name AS entidade_consumida,
    e.entity_type AS tipo_entidade,
    u.role AS papel_uso,
    u.used_at AS usado_em
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rf}
  AND a.activity_type = 'wrapper_execution';""",
        ),
        query(
            "9",
            "PROV: wrapper gerou lote normalizado (generated)",
            "prov_core_prov_generated wrapper → normalized_batch.",
            "Formaliza produção do lote normalizado.",
            "Uma linha; entidade_gerada é o lote do mesmo run.",
            f"""SELECT
    a.name AS nome_atividade,
    e.name AS entidade_gerada,
    e.entity_type AS tipo_entidade,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rf}
  AND a.activity_type = 'wrapper_execution';""",
        ),
        section("4. INTEGRAÇÃO SEMÂNTICA E ONTOLOGIA"),
        query(
            "10",
            "Integração semântica sobre o lote normalizado",
            "semantic_integration_execution com ontologia e status.",
            "Mapeia lote tabular para modelo canônico/ontológico.",
            "Uma execução; normalized_batch_id = lote do run.",
            f"""SELECT
    sie.semantic_integration_execution_id AS id_integracao_semantica,
    sie.ontology_name AS ontologia,
    sie.ontology_version AS versao_ontologia,
    sie.execution_status AS status_integracao,
    sie.started_at AS inicio_integracao,
    sie.normalized_batch_id AS id_lote_entrada,
    sie.prov_activity_id AS id_atividade_prov_semantica
FROM semantic_semantic_integration_execution AS sie
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sie.pipeline_run_id
WHERE {rf};""",
        ),
        query(
            "11",
            "Snapshot canônico anual",
            "canonical_snapshot usado como base do cálculo.",
            "Base semântica estável para o método GHG.",
            "Uma linha; snapshot_hash para integridade.",
            f"""SELECT
    cs.canonical_snapshot_id AS id_snapshot,
    cs.snapshot_label AS rotulo_snapshot,
    cs.graph_name AS nome_grafo,
    cs.snapshot_hash AS hash_snapshot,
    cs.published_at AS publicado_em,
    cs.prov_entity_id AS id_entidade_prov_snapshot
FROM semantic_canonical_snapshot AS cs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE {rf};""",
        ),
        query(
            "12",
            "Itens do snapshot canônico",
            "canonical_snapshot_item com métricas atômicas.",
            "Detalha payload (ex.: produção de leite no período anual).",
            "Pode haver várias linhas por item_key; depende do demo.",
            f"""SELECT
    csi.canonical_snapshot_item_id AS id_item,
    csi.item_key AS chave_item,
    csi.item_hash AS hash_item,
    csi.payload AS conteudo_json
FROM semantic_canonical_snapshot_item AS csi
WHERE csi.canonical_snapshot_id IN (
    SELECT cs.canonical_snapshot_id
    FROM semantic_canonical_snapshot AS cs
    INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
    WHERE {rf}
);""",
        ),
        query(
            "13",
            "Publicação canônica na ontologia (ontology resource link)",
            "ontology_resource_link do snapshot canônico.",
            "Vínculo do snapshot com recurso ontológico publicado.",
            "publication_stage canônico; ontology_uri do demo.",
            f"""SELECT
    orl.ontology_resource_link_id AS id_link,
    orl.ontology_uri AS uri_ontologia,
    orl.rdf_class AS classe_rdf,
    orl.graph_name AS nome_grafo,
    orl.publication_stage AS estagio_publicacao,
    orl.published_at AS publicado_em
FROM semantic_ontology_resource_link AS orl
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = orl.pipeline_run_id
WHERE {rf};""",
        ),
        query(
            "14",
            "PROV: integração usou lote normalizado (used)",
            "used semantic_integration → normalized_batch.",
            "Amarra integração ao insumo correto.",
            "Uma linha principal.",
            f"""SELECT
    a.name AS nome_atividade,
    e.name AS entidade_consumida,
    e.entity_type AS tipo_entidade,
    u.used_at AS usado_em
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rf}
  AND a.activity_type = 'semantic_integration';""",
        ),
        query(
            "15",
            "PROV: integração gerou snapshot canônico (generated)",
            "generated semantic_integration → canonical_snapshot.",
            "Fecha etapa semântica com saída auditável.",
            "Uma linha; entidade_gerada é o snapshot do run.",
            f"""SELECT
    a.name AS nome_atividade,
    e.name AS entidade_gerada,
    e.entity_type AS tipo_entidade,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rf}
  AND a.activity_type = 'semantic_integration';""",
        ),
        section("5. AGREGAÇÃO (VERIFICAÇÃO DE AUSÊNCIA NESTE CENÁRIO)"),
        query(
            "16",
            "Verificação: sem monthly_aggregation",
            "Busca atividades monthly_aggregation no run.",
            "Cenário anual direto não possui rollup mensal.",
            "Resultado esperado: zero linhas.",
            f"""SELECT
    a.activity_id AS id_atividade,
    a.name AS nome_atividade
FROM prov_core_prov_activity AS a
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rf}
  AND a.name LIKE '%monthly_aggregation%';""",
        ),
        query(
            "17",
            "Verificação: sem annual_aggregation",
            "Busca atividade annual_aggregation no run.",
            "Dado já é anual; não há segunda agregação anual.",
            "Resultado esperado: zero linhas.",
            f"""SELECT
    a.activity_id AS id_atividade,
    a.name AS nome_atividade
FROM prov_core_prov_activity AS a
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rf}
  AND a.name = 'annual_aggregation';""",
        ),
        calc_review_hash_blocks(rf),
        prov_block(cw, "São Pedro"),
        section("10. LINHAGEM COMPLETA DO CASO"),
        query(
            "—",
            "Linhagem resumida ponta a ponta (narrativa)",
            "UNION ordenado das principais etapas do caso anual direto.",
            "Fechamento da apresentação em uma consulta.",
            "ordem_etapa 1..10 do pipeline_run ao blockchain_anchor.",
            f"""SELECT
    1 AS ordem_etapa,
    'pipeline_run' AS etapa_pipeline,
    r.run_code AS codigo_execucao,
    r.reporting_period_reference AS periodo,
    r.run_status AS status,
    'Início da linhagem (anual direto)' AS observacao
FROM pipeline_pipeline_run AS r
WHERE {rf}
UNION ALL
SELECT 2, 'source_artifact', sa.original_filename, r.reporting_period_reference, 'received', sa.content_hash
FROM pipeline_source_artifact AS sa
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sa.pipeline_run_id
WHERE {rf}
UNION ALL
SELECT 3, 'wrapper_execution', we.wrapper_execution_id, r.reporting_period_reference, we.execution_status, 'Bruto para lote normalizado'
FROM pipeline_wrapper_execution AS we
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = we.pipeline_run_id
WHERE {rf}
UNION ALL
SELECT 4, 'normalized_batch', nb.batch_code, r.reporting_period_reference, 'generated', nb.content_hash
FROM pipeline_normalized_batch AS nb
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = nb.pipeline_run_id
WHERE {rf}
UNION ALL
SELECT 5, 'semantic_integration', sie.semantic_integration_execution_id, r.reporting_period_reference, sie.execution_status, 'Mapeamento ontológico'
FROM semantic_semantic_integration_execution AS sie
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sie.pipeline_run_id
WHERE {rf}
UNION ALL
SELECT 6, 'canonical_snapshot', cs.snapshot_label, r.reporting_period_reference, 'published', cs.snapshot_hash
FROM semantic_canonical_snapshot AS cs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE {rf}
UNION ALL
SELECT 7, 'calculation_execution', ce.calculation_execution_id, r.reporting_period_reference, ce.execution_status, 'Cálculo sobre snapshot anual'
FROM calculation_calculation_execution AS ce
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ce.pipeline_run_id
WHERE {rf}
UNION ALL
SELECT 8, 'result_set', rs.calculation_result_set_id, r.reporting_period_reference, rs.result_set_status, 'Resultado, revisão e publicação'
FROM calculation_calculation_result_set AS rs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE {rf}
UNION ALL
SELECT 9, 'hash_record', hr.hash_record_id, r.reporting_period_reference, hr.subject_kind, hr.hash_value
FROM audit_hash_record AS hr
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = hr.pipeline_run_id
WHERE {rf}
UNION ALL
SELECT 10, 'blockchain_anchor', ba.blockchain_anchor_id, r.reporting_period_reference, ba.anchor_status, ba.transaction_hash
FROM audit_blockchain_anchor AS ba
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ba.pipeline_run_id
WHERE {rf}
ORDER BY ordem_etapa;""",
        ),
        query(
            "—",
            "Cadeia operacional (join spine no run único)",
            "Join das tabelas críticas no mesmo pipeline_run.",
            "Visão técnica para auditoria cruzada de FKs.",
            "Uma linha se o demo estiver completo.",
            f"""SELECT
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
WHERE {rf};""",
        ),
    ]
    return "\n".join(parts)


def build_queries_02() -> str:
    farm = "Fazenda Boa Vista"
    monthly_f = (
        "r.farm_reference = 'Fazenda Boa Vista' "
        "AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' "
        "AND r.run_code NOT LIKE '%-annual'"
    )
    annual_run = "demo_repo_boa_vista_2026-annual"
    ar = f"r.run_code = '{annual_run}'"
    case_where = "r.run_code LIKE 'demo_repo_boa_vista_2026%'"
    parts = [
        file_header(
            "CASO 2: FAZENDA BOA VISTA — MENSAL PARA ANUAL",
            farm,
            "monthly (12 runs) → annual_aggregation → cálculo no run anual",
            [
                "Identificação da execução",
                "Entrada de dados brutos (12 meses)",
                "Wrapper e normalização (12 meses)",
                "Integração semântica e ontologia (12 meses)",
                "Agregação anual (12 → 1)",
                "Cálculo e resultado preliminar (run anual)",
                "Aprovação humana e publicação final",
                "Hashes e blockchain simulado",
                "Relações formais de proveniência",
                "Linhagem completa do caso",
            ],
            "queries_02_monthly_to_annual_pipeline.sql",
            "--   Mensais: demo_repo_boa_vista_2026-01 .. 2026-12\n"
            f"--   Anual:  {annual_run}",
        ),
        section("1. IDENTIFICAÇÃO DA EXECUÇÃO DA PIPELINE"),
        query(
            "1",
            "Mapa de execuções (12 mensais + run anual)",
            "Todos os pipeline_run da Fazenda Boa Vista no demo.",
            "Separa processamento mensal da consolidação/cálculo anual.",
            "13 linhas: 12 com run_code 2026-NN e uma linha -annual.",
            f"""SELECT
    r.pipeline_run_id AS id_execucao_pipeline,
    r.run_code AS codigo_execucao,
    r.reporting_period_reference AS periodo_referencia,
    r.run_status AS status_execucao,
    r.started_at AS inicio_execucao
FROM pipeline_pipeline_run AS r
WHERE r.farm_reference = '{farm}'
  AND r.run_code LIKE 'demo_repo_boa_vista_2026%'
ORDER BY r.reporting_period_reference, r.run_code;""",
        ),
        query(
            "2",
            "Bundles de proveniência por execução",
            "Bundles PROV em cada run mensal e no run anual.",
            "Organiza o grafo por fase e por período.",
            "Runs mensais: wrapper/semantic; run anual: calculation/publication.",
            f"""SELECT
    r.run_code AS codigo_execucao,
    b.bundle_type AS tipo_bundle,
    b.status AS status_bundle,
    b.created_at AS criado_em
FROM prov_core_prov_bundle AS b
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = b.pipeline_run_id
WHERE r.farm_reference = '{farm}'
  AND r.run_code LIKE 'demo_repo_boa_vista_2026%'
ORDER BY r.run_code, b.bundle_type;""",
        ),
        query(
            "3",
            "Agentes do demo (disparo, agregação, revisão)",
            "Agentes referenciados no population demo.",
            "Responsabilidade operacional e de aprovação.",
            "Filtra external_reference demo:%.",
            """SELECT
    ag.agent_id AS id_agente,
    ag.agent_type AS tipo_agente,
    ag.name AS nome_agente,
    ag.external_reference AS referencia_externa
FROM prov_core_prov_agent AS ag
WHERE ag.external_reference LIKE 'demo:%'
ORDER BY ag.agent_type, ag.name;""",
        ),
        section("2. ENTRADA DE DADOS BRUTOS (12 MESES)"),
        query(
            "4",
            "Artefatos brutos mensais (12 source_artifact)",
            "Um artefato por mês (jan–dez/2026).",
            "Matéria-prima da cadeia e insumo indireto da agregação anual.",
            "12 linhas ordenadas por periodo_referencia.",
            f"""SELECT
    r.run_code AS codigo_execucao,
    r.reporting_period_reference AS mes_referencia,
    sa.source_artifact_id AS id_artefato_bruto,
    sa.original_filename AS arquivo_original,
    sa.content_hash AS hash_conteudo,
    sa.received_at AS recebido_em
FROM pipeline_source_artifact AS sa
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sa.pipeline_run_id
WHERE {monthly_f}
ORDER BY r.reporting_period_reference;""",
        ),
        section("3. WRAPPER E NORMALIZAÇÃO (12 MESES)"),
        query(
            "5",
            "Definição de wrapper utilizada",
            "Catálogo wrapper_definition do demo.",
            "Mesma transformação em todos os meses.",
            "demo-repo-normalizer.",
            """SELECT
    wd.wrapper_name AS nome_wrapper,
    wd.wrapper_version AS versao_wrapper,
    wd.source_layout_name AS layout_fonte
FROM pipeline_wrapper_definition AS wd
WHERE wd.wrapper_name = 'demo-repo-normalizer';""",
        ),
        query(
            "6",
            "Execuções de wrapper mensais (12)",
            "wrapper_execution por run mensal.",
            "Transformação bruto → lote em cada mês.",
            "12 linhas succeeded.",
            f"""SELECT
    r.run_code AS codigo_execucao,
    we.wrapper_execution_id AS id_execucao_wrapper,
    we.execution_status AS status_wrapper,
    we.prov_activity_id AS id_atividade_prov
FROM pipeline_wrapper_execution AS we
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = we.pipeline_run_id
WHERE {monthly_f}
ORDER BY r.reporting_period_reference;""",
        ),
        query(
            "7",
            "Lotes normalizados mensais (12)",
            "normalized_batch por mês.",
            "Insumo da integração semântica mensal.",
            "12 linhas; record_count tipicamente 1.",
            f"""SELECT
    r.run_code AS codigo_execucao,
    nb.batch_code AS codigo_lote,
    nb.record_count AS quantidade_registros,
    nb.content_hash AS hash_lote
FROM pipeline_normalized_batch AS nb
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = nb.pipeline_run_id
WHERE {monthly_f}
ORDER BY r.reporting_period_reference;""",
        ),
        query(
            "8",
            "PROV: wrappers consumiram bruto mensal (used)",
            "Lista used wrapper → source_artifact nos 12 meses.",
            "12 consumos explícitos em PROV.",
            "Contagem mental = 12.",
            f"""SELECT
    r.run_code AS codigo_execucao,
    e.name AS entidade_consumida,
    u.role AS papel_uso
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {monthly_f}
  AND a.activity_type = 'wrapper_execution'
ORDER BY r.run_code;""",
        ),
        query(
            "9",
            "PROV: wrappers geraram lotes mensais (generated)",
            "Lista generated wrapper → normalized_batch.",
            "12 produções em PROV.",
            "Uma por run_code mensal.",
            f"""SELECT
    r.run_code AS codigo_execucao,
    e.name AS entidade_gerada,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {monthly_f}
  AND a.activity_type = 'wrapper_execution'
ORDER BY r.run_code;""",
        ),
        section("4. INTEGRAÇÃO SEMÂNTICA E ONTOLOGIA (12 MESES)"),
        query(
            "10",
            "Integrações semânticas mensais (12)",
            "semantic_integration_execution por mês.",
            "Produz snapshots canônicos mensais.",
            "12 linhas execution_status succeeded.",
            f"""SELECT
    r.run_code AS codigo_execucao,
    sie.semantic_integration_execution_id AS id_integracao,
    sie.execution_status AS status_integracao,
    sie.ontology_name AS ontologia
FROM semantic_semantic_integration_execution AS sie
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = sie.pipeline_run_id
WHERE {monthly_f}
ORDER BY r.reporting_period_reference;""",
        ),
        query(
            "11",
            "Snapshots canônicos mensais (12)",
            "canonical_snapshot por mês — entradas da annual_aggregation.",
            "Cada snapshot mensal é insumo da agregação anual.",
            "12 linhas com prov_entity_id distintos.",
            f"""SELECT
    r.run_code AS codigo_execucao,
    cs.canonical_snapshot_id AS id_snapshot,
    cs.snapshot_label AS rotulo_snapshot,
    cs.snapshot_hash AS hash_snapshot
FROM semantic_canonical_snapshot AS cs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE {monthly_f}
ORDER BY r.reporting_period_reference;""",
        ),
        query(
            "12",
            "Itens dos snapshots mensais (amostra)",
            "canonical_snapshot_item dos 12 meses.",
            "Detalhe de métricas por mês.",
            "Várias linhas; ordenado por run e item_key.",
            f"""SELECT
    r.run_code AS codigo_execucao,
    csi.item_key AS chave_item,
    csi.payload AS conteudo_json
FROM semantic_canonical_snapshot_item AS csi
INNER JOIN semantic_canonical_snapshot AS cs
    ON cs.canonical_snapshot_id = csi.canonical_snapshot_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE {monthly_f}
ORDER BY r.run_code, csi.item_key;""",
        ),
        query(
            "13",
            "Links ontológicos canônicos mensais",
            "ontology_resource_link por run mensal.",
            "Publicação canônica de cada mês.",
            "Até 12 linhas.",
            f"""SELECT
    r.run_code AS codigo_execucao,
    orl.ontology_uri AS uri_ontologia,
    orl.publication_stage AS estagio
FROM semantic_ontology_resource_link AS orl
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = orl.pipeline_run_id
WHERE {monthly_f}
ORDER BY r.run_code;""",
        ),
        query(
            "14",
            "PROV: integrações usaram lotes mensais (used)",
            "used semantic_integration → normalized_batch (12).",
            "Ligação semântica mensal em PROV.",
            "12 linhas.",
            f"""SELECT
    r.run_code AS codigo_execucao,
    e.name AS lote_consumido
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {monthly_f}
  AND a.activity_type = 'semantic_integration'
ORDER BY r.run_code;""",
        ),
        query(
            "15",
            "PROV: integrações geraram snapshots mensais (generated)",
            "generated semantic_integration → canonical_snapshot (12).",
            "Saída semântica mensal formalizada.",
            "12 linhas.",
            f"""SELECT
    r.run_code AS codigo_execucao,
    e.name AS snapshot_gerado
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {monthly_f}
  AND a.activity_type = 'semantic_integration'
ORDER BY r.run_code;""",
        ),
        section("5. AGREGAÇÃO ANUAL (12 MENSais → 1 AGREGADO)"),
        query(
            "16",
            "Atividade annual_aggregation",
            "prov_activity annual_aggregation no run anual.",
            "Consolida os 12 snapshots mensais.",
            "Uma atividade no run demo_repo_boa_vista_2026-annual.",
            f"""SELECT
    a.activity_id AS id_atividade,
    a.name AS nome_atividade,
    a.status AS status_atividade,
    a.started_at AS inicio,
    a.ended_at AS fim
FROM prov_core_prov_activity AS a
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {ar}
  AND a.name = 'annual_aggregation';""",
        ),
        query(
            "17",
            "Entradas da annual_aggregation (lista das 12 mensais)",
            "prov_used com role aggregation_input — snapshots mensais.",
            "Evidência lista da cardinalidade da agregação.",
            "12 linhas com nomes dos snapshots fonte.",
            f"""SELECT
    se.name AS snapshot_mensal_fonte,
    u.role AS papel,
    u.used_at AS usado_em
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN prov_core_prov_entity AS se ON se.entity_id = u.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {ar}
  AND a.name = 'annual_aggregation'
ORDER BY u.used_at;""",
        ),
        query(
            "18",
            "Validação: annual_aggregation com 12 entradas",
            "Contagem de prov_used na agregação anual.",
            "Invariante do demo: exatamente 12 meses.",
            "Coluna entradas_mensais deve ser 12.",
            f"""SELECT
    COUNT(u.used_id) AS entradas_mensais
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {ar}
  AND a.name = 'annual_aggregation';""",
        ),
        query(
            "19",
            "Entidade annual_aggregate",
            "prov_entity entity_kind annual-aggregation.",
            "Produto da agregação; insumo lógico do cálculo anual.",
            "Uma entidade no run anual.",
            f"""SELECT
    e.entity_id AS id_entidade,
    e.entity_kind AS kind_entidade,
    e.name AS nome_entidade,
    e.content_hash AS hash_entidade
FROM prov_core_prov_entity AS e
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = e.pipeline_run_id
WHERE {ar}
  AND e.entity_kind = 'annual-aggregation';""",
        ),
        query(
            "20",
            "PROV: annual_aggregate gerado pela agregação (generated)",
            "generated annual_aggregation → annual_aggregate.",
            "Saída formal da atividade de agregação.",
            "Uma linha.",
            f"""SELECT
    e.name AS entidade_agregada,
    g.generated_at AS gerado_em
FROM prov_core_prov_generated AS g
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = g.activity_id
INNER JOIN prov_core_prov_entity AS e ON e.entity_id = g.entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {ar}
  AND a.name = 'annual_aggregation';""",
        ),
        query(
            "21",
            "PROV: annual_aggregate deriva dos 12 meses (derived_from)",
            "derived_from mensal → agregado anual.",
            "Linhagem rollup explícita em PROV.",
            "12 linhas derivation_type annual_aggregation.",
            f"""SELECT
    se.name AS fonte_mensal,
    ge.name AS agregado_anual,
    d.derivation_type AS tipo_derivacao
FROM prov_core_prov_derived_from AS d
INNER JOIN prov_core_prov_entity AS ge ON ge.entity_id = d.generated_entity_id
INNER JOIN prov_core_prov_entity AS se ON se.entity_id = d.source_entity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ge.pipeline_run_id
WHERE {ar}
  AND d.derivation_type = 'annual_aggregation'
ORDER BY se.name;""",
        ),
        query(
            "22",
            "Métrica de negócio: produção agregada (validação)",
            "calculation_result_item aggregated_milk_production no run anual.",
            "Validação quantitativa esperada (~150500 L no demo).",
            "Uma linha com result_value e result_unit.",
            f"""SELECT
    ri.result_name AS nome_metrica,
    ri.result_value AS valor,
    ri.result_unit AS unidade
FROM calculation_calculation_result_item AS ri
INNER JOIN calculation_calculation_result_set AS rs
    ON rs.calculation_result_set_id = ri.calculation_result_set_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE {ar}
  AND ri.result_name = 'aggregated_milk_production';""",
        ),
        calc_review_hash_blocks(ar),
        prov_block(case_where, "Boa Vista"),
        section("10. LINHAGEM COMPLETA DO CASO"),
        query(
            "—",
            "Contagens por fase da pipeline",
            "Resumo quantitativo: mensais, agregação, publicação.",
            "Slide de fechamento com números-chave.",
            "mensal=12; entradas_agregacao=12; publicacao_anual=1.",
            f"""SELECT 'runs_mensais' AS fase, COUNT(*) AS quantidade
FROM pipeline_pipeline_run AS r
WHERE {monthly_f}
UNION ALL
SELECT 'atividade_annual_aggregation', COUNT(*)
FROM prov_core_prov_activity AS a
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {ar} AND a.name = 'annual_aggregation'
UNION ALL
SELECT 'entradas_na_agregacao', COUNT(*)
FROM prov_core_prov_used AS u
INNER JOIN prov_core_prov_activity AS a ON a.activity_id = u.activity_id
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {ar} AND a.name = 'annual_aggregation'
UNION ALL
SELECT 'publicacao_anual', COUNT(*)
FROM calculation_result_publication_execution AS pe
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = pe.pipeline_run_id
WHERE {ar};""",
        ),
        query(
            "—",
            "Linhagem resumida mensal → anual (narrativa)",
            "UNION das etapas principais até hash no run anual.",
            "Narrativa ponta a ponta para banca.",
            "ordem_etapa crescente; último passo blockchain no run anual.",
            f"""SELECT
    1 AS ordem_etapa,
    '12_runs_mensais' AS etapa_pipeline,
    CAST(COUNT(*) AS TEXT) AS referencia,
    'monthly' AS periodo,
    'succeeded' AS status,
    'Bruto mensal por mês' AS observacao
FROM pipeline_pipeline_run AS r
WHERE {monthly_f}
UNION ALL
SELECT 2, 'annual_aggregation', a.name, r.reporting_period_reference, a.status, 'Consolida 12 snapshots'
FROM prov_core_prov_activity AS a
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {ar} AND a.name = 'annual_aggregation'
UNION ALL
SELECT 3, 'annual_aggregate', e.name, r.reporting_period_reference, e.entity_kind, 'Entidade agregada'
FROM prov_core_prov_entity AS e
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = e.pipeline_run_id
WHERE {ar} AND e.entity_kind = 'annual-aggregation'
UNION ALL
SELECT 4, 'calculation_execution', ce.calculation_execution_id, r.reporting_period_reference, ce.execution_status, 'Cálculo sobre agregado'
FROM calculation_calculation_execution AS ce
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ce.pipeline_run_id
WHERE {ar}
UNION ALL
SELECT 5, 'result_set', rs.calculation_result_set_id, r.reporting_period_reference, rs.result_set_status, 'Resultado e governança'
FROM calculation_calculation_result_set AS rs
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE {ar}
UNION ALL
SELECT 6, 'blockchain_anchor', ba.blockchain_anchor_id, r.reporting_period_reference, ba.anchor_status, ba.transaction_hash
FROM audit_blockchain_anchor AS ba
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ba.pipeline_run_id
WHERE {ar}
ORDER BY ordem_etapa;""",
        ),
        query(
            "—",
            "Verificação: cálculo no run anual (não 12 cálculos mensais)",
            "Contagem de calculation_execution no run anual.",
            "O total anual vem de um cálculo sobre o agregado.",
            "execucoes_calculo_run_anual = 1.",
            f"""SELECT
    COUNT(*) AS execucoes_calculo_run_anual
FROM calculation_calculation_execution AS ce
INNER JOIN pipeline_pipeline_run AS r ON r.pipeline_run_id = ce.pipeline_run_id
WHERE {ar};""",
        ),
        query(
            "—",
            "Cadeia operacional do run anual (join spine)",
            "Join das tabelas críticas no run anual de consolidação.",
            "Visão técnica pós-agregação.",
            "Uma linha com snapshot, cálculo, resultado, revisão e publicação.",
            f"""SELECT
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
WHERE {ar};""",
        ),
    ]
    return "\n".join(parts)


def main() -> None:
    files = {
        "queries_01_annual_direct_pipeline.sql": build_queries_01(),
        "queries_02_monthly_to_annual_pipeline.sql": build_queries_02(),
    }
    for name, content in files.items():
        path = OUT / name
        path.write_text(content.strip() + "\n", encoding="utf-8")
        n = content.count("SELECT")
        print(f"Wrote {path.name} (~{n} SELECT blocks)")


if __name__ == "__main__":
    main()
