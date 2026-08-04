"""One-off generator for presentation SQL files. Not part of runtime demo."""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).parent


def block(step: str, title: str, shows: str, why: str, prov: str, sql: str) -> str:
    prov_lines = "\n".join(f"-- - {line}" for line in prov.split("\n") if line.strip())
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
-- Relações de proveniência demonstradas:
{prov_lines}
{sql.strip()}
"""


def header(case_num: int, title: str, farm: str, gran: str, summary: str, filename: str) -> str:
    return f"""-- ============================================================
-- {title}
-- ============================================================
--
-- Objetivo:
-- Demonstrar query por query como a proveniência foi registrada
-- no SQLite para este cenário de demonstração.
--
-- Fazenda / personagem: {farm}
-- Granularidade principal: {gran}
--
-- Resumo da pipeline:
-- {summary}
--
-- Observação:
-- Este arquivo contém APENAS consultas SELECT para apresentação,
-- auditoria visual e explicação. Não há INSERT, UPDATE ou DELETE.
--
-- Pré-requisito:
-- Executar antes: python scripts/demo_repository_full_population/run_all.py
--
-- Execução sugerida:
-- sqlite3 data/provenance.db < scripts/demo_repository_full_population/{filename}
--
"""


def prov_section(case_filter_sql: str) -> str:
    return f"""
-- ============================================================
-- RELAÇÕES FORMAIS DE PROVENIÊNCIA DO CASO
-- ============================================================

-- ------------------------------------------------------------
-- PROV 1 — Todas as relações used do caso
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Entidades consumidas por atividades (prov:used / wasUsedBy).
--
-- Por que isso importa:
-- Prova quais insumos cada etapa da pipeline utilizou.
--
-- Relações de proveniência demonstradas:
-- - prov_core_prov_used
SELECT
    u.used_id,
    r.run_code,
    a.activity_type AS atividade_tipo,
    a.name AS atividade_nome,
    u.role AS papel,
    e.entity_type AS entidade_tipo,
    e.entity_kind AS entidade_kind,
    e.name AS entidade_nome,
    u.used_at
FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = u.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {case_filter_sql}
ORDER BY r.run_code, a.name, u.used_at;

-- ------------------------------------------------------------
-- PROV 2 — Todas as relações generated do caso
-- ------------------------------------------------------------
SELECT
    g.generated_id,
    r.run_code,
    a.activity_type AS atividade_tipo,
    a.name AS atividade_nome,
    e.entity_type AS entidade_tipo,
    e.entity_kind AS entidade_kind,
    e.name AS entidade_nome,
    g.generated_at
FROM prov_core_prov_generated g
JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = g.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {case_filter_sql}
ORDER BY r.run_code, g.generated_at;

-- ------------------------------------------------------------
-- PROV 3 — Todas as relações derived_from do caso
-- ------------------------------------------------------------
SELECT
    d.derived_id,
    r.run_code,
    d.derivation_type,
    ge.name AS entidade_gerada,
    ge.entity_kind AS kind_gerada,
    se.name AS entidade_fonte,
    se.entity_kind AS kind_fonte
FROM prov_core_prov_derived_from d
JOIN prov_core_prov_entity ge ON ge.entity_id = d.generated_entity_id
JOIN prov_core_prov_entity se ON se.entity_id = d.source_entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ge.pipeline_run_id
WHERE {case_filter_sql}
ORDER BY r.run_code, d.derivation_type;

-- ------------------------------------------------------------
-- PROV 4 — Todas as relações associated_with do caso
-- ------------------------------------------------------------
SELECT
    aw.association_id,
    r.run_code,
    a.name AS atividade_nome,
    a.activity_type AS atividade_tipo,
    ag.name AS agente_nome,
    ag.agent_type AS agente_tipo,
    aw.role AS papel
FROM prov_core_prov_associated_with aw
JOIN prov_core_prov_activity a ON a.activity_id = aw.activity_id
JOIN prov_core_prov_agent ag ON ag.agent_id = aw.agent_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {case_filter_sql}
ORDER BY r.run_code, a.name;

-- ------------------------------------------------------------
-- PROV 5 — Relações revision do caso (se existirem)
-- ------------------------------------------------------------
SELECT
    pr.revision_id,
    pr.revision_reason,
    pr.revised_at,
    pe.name AS entidade_anterior,
    ne.name AS entidade_nova
FROM prov_core_prov_revision pr
JOIN prov_core_prov_entity pe ON pe.entity_id = pr.previous_entity_id
JOIN prov_core_prov_entity ne ON ne.entity_id = pr.new_entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ne.pipeline_run_id
WHERE {case_filter_sql}
ORDER BY pr.revised_at;

-- ------------------------------------------------------------
-- PROV 6 — Resumo tabular do grafo de proveniência
-- ------------------------------------------------------------
SELECT
    r.run_code,
    a.name AS atividade,
    a.activity_type AS atividade_tipo,
    u.role AS relacao,
    'used' AS tipo_relacao,
    se.name AS entidade_entrada,
    NULL AS entidade_saida,
    NULL AS agente
FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN prov_core_prov_entity se ON se.entity_id = u.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {case_filter_sql}
UNION ALL
SELECT
    r.run_code,
    a.name,
    a.activity_type,
    NULL,
    'generated',
    NULL,
    ge.name,
    NULL
FROM prov_core_prov_generated g
JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id
JOIN prov_core_prov_entity ge ON ge.entity_id = g.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {case_filter_sql}
UNION ALL
SELECT
    r.run_code,
    NULL,
    NULL,
    d.derivation_type,
    'derived_from',
    se.name,
    ge.name,
    NULL
FROM prov_core_prov_derived_from d
JOIN prov_core_prov_entity ge ON ge.entity_id = d.generated_entity_id
JOIN prov_core_prov_entity se ON se.entity_id = d.source_entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ge.pipeline_run_id
WHERE {case_filter_sql}
ORDER BY run_code, tipo_relacao, atividade;
"""


def build_annual_direct() -> str:
    run = "demo_repo_sao_pedro_2026"
    farm = "Fazenda São Pedro"
    cf = f"r.run_code = '{run}'"
    parts = [
        header(
            1,
            "CASO 1: FAZENDA SÃO PEDRO — DADO ANUAL DIRETO",
            farm,
            "annual (anual direto, sem agregação)",
            "dado bruto anual → wrapper → lote normalizado → integração semântica → snapshot canônico → cálculo → resultado → aprovação → publicação → hash → blockchain",
            "queries_01_annual_direct_pipeline.sql",
        ),
        block(
            "1",
            "Identificação do pipeline_run",
            f"O pipeline_run principal do caso ({run}).",
            "É a raiz operacional de toda a linhagem deste cenário.",
            "Nenhuma relação PROV direta; ancora bundles e entidades.",
            f"""SELECT
    r.pipeline_run_id,
    r.run_code,
    r.farm_reference,
    r.reporting_period_reference,
    r.run_status,
    r.started_at,
    r.parent_pipeline_run_id,
    r.idempotency_key
FROM pipeline_pipeline_run r
WHERE r.run_code = '{run}';""",
        ),
        block(
            "2",
            "Bundles de proveniência",
            "Bundles PROV agrupando entidades e atividades por etapa.",
            "Organiza o grafo W3C PROV por fase da pipeline.",
            "prov_core_prov_bundle ligado ao pipeline_run.",
            f"""SELECT
    b.bundle_id,
    b.bundle_type,
    b.status AS bundle_status,
    b.name AS bundle_name,
    b.created_at
FROM prov_core_prov_bundle b
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = b.pipeline_run_id
WHERE r.run_code = '{run}'
ORDER BY b.bundle_type;""",
        ),
        block(
            "3",
            "Agentes envolvidos",
            "Agentes humanos/software que disparam ou revisam o fluxo.",
            "Atribui responsabilidade (quem executou / quem aprovou).",
            "associated_with na revisão; triggered_by no pipeline_run.",
            f"""SELECT DISTINCT
    ag.agent_id,
    ag.agent_type,
    ag.name AS agente_nome,
    ag.external_reference
FROM prov_core_prov_agent ag
WHERE ag.agent_id IN (
    SELECT r.triggered_by_agent_id FROM pipeline_pipeline_run r WHERE r.run_code = '{run}'
    UNION
    SELECT cr.reviewer_agent_id
    FROM calculation_calculation_review cr
    JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cr.pipeline_run_id
    WHERE r.run_code = '{run}'
);""",
        ),
    ]
    # Continue with pipeline entities - I'll append programmatically for steps 4-36
    steps = _annual_steps(run, farm)
    parts.extend(steps)
    parts.append(prov_section(cf))
    parts.append(_final_lineage_annual(run))
    return "\n".join(parts)


def _annual_steps(run: str, farm: str) -> list[str]:
    rfilter = f"r.run_code = '{run}'"
    s: list[str] = []

    def q(step, title, shows, why, prov, sql):
        s.append(block(step, title, shows, why, prov, sql))

    q(
        "4",
        "Source artifact anual (dado bruto)",
        "Artefato de entrada representando o arquivo/dado bruto anual.",
        "Primeiro registro material da cadeia; base para wrapper e hashes.",
        "Entidade PROV source_artifact espelhada em prov_core_prov_entity.",
        f"""SELECT
    sa.source_artifact_id,
    sa.original_filename,
    sa.source_system,
    sa.storage_uri,
    sa.content_hash,
    sa.received_at,
    sa.prov_entity_id
FROM pipeline_source_artifact sa
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = sa.pipeline_run_id
WHERE {rfilter};""",
    )
    q(
        "5",
        "Wrapper definition usada",
        "Definição de wrapper (catálogo) referenciada pela execução.",
        "Documenta qual transformação layout→normalizado foi aplicada.",
        "Nenhuma relação PROV direta; referência operacional.",
        f"""SELECT
    wd.wrapper_definition_id,
    wd.wrapper_name,
    wd.wrapper_version,
    wd.source_layout_name,
    wd.code_hash
FROM pipeline_wrapper_definition wd
WHERE wd.wrapper_definition_id IN (
    SELECT we.wrapper_definition_id
    FROM pipeline_wrapper_execution we
    JOIN pipeline_pipeline_run r ON r.pipeline_run_id = we.pipeline_run_id
    WHERE {rfilter}
);""",
    )
    q(
        "6",
        "Wrapper execution anual",
        "Execução do wrapper sobre o dado bruto.",
        "Atividade de transformação entre bruto e lote normalizado.",
        "prov_activity wrapper_execution; used/generated nas etapas 8-9.",
        f"""SELECT
    we.wrapper_execution_id,
    we.execution_status,
    we.started_at,
    we.finished_at,
    we.input_artifact_id,
    we.prov_activity_id
FROM pipeline_wrapper_execution we
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = we.pipeline_run_id
WHERE {rfilter};""",
    )
    q(
        "7",
        "Normalized batch anual",
        "Lote normalizado produzido pelo wrapper.",
        "Formato intermediário consumido pela integração semântica.",
        "Entidade normalized_batch; derived_from do bruto.",
        f"""SELECT
    nb.normalized_batch_id,
    nb.batch_code,
    nb.schema_version,
    nb.record_count,
    nb.content_hash,
    nb.generated_at,
    nb.prov_entity_id
FROM pipeline_normalized_batch nb
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = nb.pipeline_run_id
WHERE {rfilter};""",
    )
    q(
        "8",
        "PROV: wrapper usou dado bruto",
        "Relação used entre atividade de wrapper e entidade source_artifact.",
        "Prova que o wrapper consumiu explicitamente o bruto.",
        "prov_core_prov_used (wasUsedBy).",
        f"""SELECT
    u.used_id,
    a.name AS wrapper_atividade,
    e.name AS entidade_usada,
    e.entity_type,
    u.role,
    u.used_at
FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = u.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rfilter}
  AND a.activity_type = 'wrapper_execution';""",
    )
    q(
        "9",
        "PROV: wrapper gerou lote normalizado",
        "Relação generated da atividade de wrapper para entidade normalized_batch.",
        "Prova a produção do lote como saída da transformação.",
        "prov_core_prov_generated (wasGeneratedBy).",
        f"""SELECT
    g.generated_id,
    a.name AS wrapper_atividade,
    e.name AS entidade_gerada,
    e.entity_type,
    g.generated_at
FROM prov_core_prov_generated g
JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = g.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rfilter}
  AND a.activity_type = 'wrapper_execution';""",
    )
    q(
        "10",
        "Semantic integration execution",
        "Execução da integração semântica sobre o lote normalizado.",
        "Ponte entre dados tabulares/normalizados e grafo canônico.",
        "prov_activity semantic_integration.",
        f"""SELECT
    sie.semantic_integration_execution_id,
    sie.ontology_name,
    sie.ontology_version,
    sie.execution_status,
    sie.started_at,
    sie.finished_at,
    sie.normalized_batch_id,
    sie.prov_activity_id
FROM semantic_semantic_integration_execution sie
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = sie.pipeline_run_id
WHERE {rfilter};""",
    )
    q(
        "11",
        "Canonical snapshot anual",
        "Snapshot canônico publicado para cálculo.",
        "Base semântica estável para execução do método.",
        "Entidade canonical_snapshot; generated pela integração.",
        f"""SELECT
    cs.canonical_snapshot_id,
    cs.snapshot_label,
    cs.graph_name,
    cs.snapshot_hash,
    cs.published_at,
    cs.prov_entity_id
FROM semantic_canonical_snapshot cs
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE {rfilter};""",
    )
    q(
        "12",
        "Canonical snapshot items",
        "Itens atômicos dentro do snapshot canônico.",
        "Detalha métricas (ex.: produção de leite) no nível item.",
        "Itens ligados ao snapshot_id.",
        f"""SELECT
    csi.canonical_snapshot_item_id,
    csi.item_key,
    csi.item_hash,
    csi.payload
FROM semantic_canonical_snapshot_item csi
WHERE csi.canonical_snapshot_id IN (
    SELECT cs.canonical_snapshot_id
    FROM semantic_canonical_snapshot cs
    JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cs.pipeline_run_id
    WHERE {rfilter}
);""",
    )
    q(
        "13",
        "PROV: integração usou lote normalizado",
        "Relação used da integração semântica sobre o normalized_batch.",
        "Amarra semantic_integration ao insumo correto.",
        "prov_core_prov_used.",
        f"""SELECT u.used_id, a.name, e.name, e.entity_type, u.used_at
FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = u.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rfilter} AND a.activity_type = 'semantic_integration';""",
    )
    q(
        "14",
        "PROV: integração gerou snapshot canônico",
        "Relação generated produzindo entidade canonical_snapshot.",
        "Fecha a etapa semântica com saída auditável.",
        "prov_core_prov_generated.",
        f"""SELECT g.generated_id, a.name, e.name, e.entity_type, g.generated_at
FROM prov_core_prov_generated g
JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = g.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rfilter} AND a.activity_type = 'semantic_integration';""",
    )
    q(
        "15",
        "Publicação canônica (ontology resource link)",
        "Vínculo do snapshot com recurso ontológico publicado.",
        "Demonstra publicação canônica na ontologia de demonstração.",
        "Entidade/recurso ontology_resource_link.",
        f"""SELECT
    orl.ontology_resource_link_id,
    orl.ontology_uri,
    orl.rdf_class,
    orl.graph_name,
    orl.publication_stage,
    orl.published_at
FROM semantic_ontology_resource_link orl
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = orl.pipeline_run_id
WHERE {rfilter};""",
    )
    # calculation block 16-29
    for step, title, sql in [
        (
            "16",
            "Calculation method",
            f"""SELECT cm.calculation_method_id, cm.method_code, cm.method_name
FROM calculation_calculation_method cm
WHERE cm.method_code = 'demo-repo-ghg-2026';""",
        ),
        (
            "17",
            "Calculation method version",
            f"""SELECT cmv.calculation_method_version_id, cmv.version_label, cmv.status
FROM calculation_calculation_method_version cmv
JOIN calculation_calculation_method cm ON cm.calculation_method_id = cmv.calculation_method_id
WHERE cm.method_code = 'demo-repo-ghg-2026';""",
        ),
        (
            "18",
            "Calculation parameter set",
            f"""SELECT cps.calculation_parameter_set_id, cps.parameter_set_status, cps.prov_entity_id
FROM calculation_calculation_parameter_set cps
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cps.pipeline_run_id
WHERE {rfilter};""",
        ),
        (
            "19",
            "Calculation parameter values",
            f"""SELECT cpv.parameter_name, cpv.parameter_value_text, cpv.parameter_value_numeric, cpv.parameter_unit
FROM calculation_calculation_parameter_value cpv
JOIN calculation_calculation_parameter_set cps ON cps.calculation_parameter_set_id = cpv.calculation_parameter_set_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cps.pipeline_run_id
WHERE {rfilter};""",
        ),
        (
            "20",
            "Calculation execution",
            f"""SELECT ce.calculation_execution_id, ce.execution_status, ce.started_at, ce.canonical_snapshot_id, ce.prov_activity_id
FROM calculation_calculation_execution ce
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ce.pipeline_run_id
WHERE {rfilter};""",
        ),
    ]:
        q(step, title, f"Dados de {title.lower()} do caso.", "Etapa do domínio calculation.", "used/generated conforme etapa.", sql)

    q(
        "21",
        "PROV: cálculo usou snapshot canônico",
        "Relação used ligando calculation_execution ao canonical_snapshot.",
        "Prova que o cálculo partiu da base canônica anual.",
        "prov_core_prov_used.",
        f"""SELECT u.used_id, a.name, e.name, e.entity_type
FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = u.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rfilter} AND a.activity_type = 'calculation_execution';""",
    )
    q(
        "22",
        "Calculation result set preliminar",
        "Conjunto de resultados gerado (status evolui após revisão).",
        "Saída quantitativa do método sobre o snapshot.",
        "prov_entity calculation_result_set; generated pelo cálculo.",
        f"""SELECT rs.calculation_result_set_id, rs.result_set_status, rs.generated_at, rs.summary_hash
FROM calculation_calculation_result_set rs
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE {rfilter};""",
    )
    q(
        "23",
        "Calculation result items",
        "Itens de resultado (métricas) do cálculo.",
        "Detalha valores como produção de leite.",
        "Itens ligados ao result_set.",
        f"""SELECT ri.result_name, ri.result_type, ri.result_value, ri.result_unit
FROM calculation_calculation_result_item ri
JOIN calculation_calculation_result_set rs ON rs.calculation_result_set_id = ri.calculation_result_set_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE {rfilter};""",
    )
    q(
        "24",
        "PROV: resultado gerado pelo cálculo",
        "Relação generated da atividade de cálculo para result_set.",
        "Liga atividade de execução ao produto quantitativo.",
        "prov_core_prov_generated.",
        f"""SELECT g.generated_id, a.name, e.name
FROM prov_core_prov_generated g
JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = g.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rfilter} AND a.activity_type = 'calculation_execution';""",
    )
    q(
        "25",
        "Calculation review (aprovação humana)",
        "Revisão humana com decisão approved.",
        "Gate de governança antes da publicação final.",
        "prov_activity calculation_review.",
        f"""SELECT cr.calculation_review_id, cr.decision, cr.review_comment, cr.reviewed_at, cr.reviewer_agent_id
FROM calculation_calculation_review cr
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cr.pipeline_run_id
WHERE {rfilter};""",
    )
    q(
        "26",
        "PROV: revisão usou resultado preliminar",
        "Relação used da revisão sobre o result_set.",
        "Prova que o revisor analisou o resultado correto.",
        "prov_core_prov_used.",
        f"""SELECT u.used_id, a.name, e.name, u.role
FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = u.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rfilter} AND a.activity_type = 'calculation_review';""",
    )
    q(
        "27",
        "PROV: agente associado à aprovação",
        "Relação associated_with entre revisão e agente humano.",
        "Atribui responsabilidade à aprovação.",
        "prov_core_prov_associated_with.",
        f"""SELECT aw.association_id, a.name AS atividade, ag.name AS agente, aw.role
FROM prov_core_prov_associated_with aw
JOIN prov_core_prov_activity a ON a.activity_id = aw.activity_id
JOIN prov_core_prov_agent ag ON ag.agent_id = aw.agent_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rfilter} AND a.activity_type = 'calculation_review';""",
    )
    q(
        "28",
        "Result publication execution",
        "Publicação final do resultado aprovado na ontologia.",
        "Última etapa funcional antes de hash/anchor.",
        "prov_activity result_publication.",
        f"""SELECT pe.result_publication_execution_id, pe.publication_status, pe.published_at, pe.target_graph_name
FROM calculation_result_publication_execution pe
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = pe.pipeline_run_id
WHERE {rfilter};""",
    )
    q(
        "29",
        "PROV: publicação usou resultado aprovado",
        "Relação used da publicação sobre result_set aprovado.",
        "Garante que só resultado aprovado foi publicado.",
        "prov_core_prov_used.",
        f"""SELECT u.used_id, a.name, e.name, u.role
FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = u.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rfilter} AND a.activity_type = 'result_publication';""",
    )
    q(
        "30",
        "Hash records do caso",
        "Registros de hash de integridade por subject_kind.",
        "Suporte à auditoria e ancoragem.",
        "audit_hash_record referenciando entidades/subjects.",
        f"""SELECT hr.hash_record_id, hr.subject_kind, hr.subject_id, hr.hash_algorithm, hr.hash_value, hr.computed_at
FROM audit_hash_record hr
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = hr.pipeline_run_id
WHERE {rfilter}
ORDER BY hr.subject_kind;""",
    )
    q(
        "31",
        "Blockchain anchors simulados",
        "Ancoragens simuladas (demo-chain) dos hashes críticos.",
        "Demonstra rastreio externo sem blockchain real.",
        "audit_blockchain_anchor → audit_hash_record.",
        f"""SELECT ba.blockchain_anchor_id, ba.blockchain_network, ba.transaction_hash, ba.anchor_status, ba.anchored_at
FROM audit_blockchain_anchor ba
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ba.pipeline_run_id
WHERE {rfilter};""",
    )
    q(
        "32",
        "Audit events do caso",
        "Eventos de auditoria (ex.: review, demo).",
        "Trilha complementar ao ledger operacional.",
        "audit_audit_event.",
        f"""SELECT ae.audit_event_id, ae.event_type, ae.subject_kind, ae.subject_id, ae.recorded_at
FROM audit_audit_event ae
WHERE ae.subject_id IN (
    SELECT rs.calculation_result_set_id FROM calculation_calculation_result_set rs
    JOIN pipeline_pipeline_run r ON r.pipeline_run_id = rs.pipeline_run_id WHERE {rfilter}
)
OR ae.event_type LIKE 'demo.%';""",
    )
    q(
        "33",
        "Outbox events do caso",
        "Eventos de outbox emitidos durante gravações.",
        "Integração assíncrona / relay de domínio.",
        "audit_outbox_event por aggregate_kind.",
        f"""SELECT oe.outbox_event_id, oe.aggregate_kind, oe.event_type, oe.status, oe.created_at
FROM audit_outbox_event oe
WHERE oe.aggregate_id IN (
    SELECT r.pipeline_run_id FROM pipeline_pipeline_run r WHERE {rfilter}
    UNION SELECT sa.source_artifact_id FROM pipeline_source_artifact sa
    JOIN pipeline_pipeline_run r ON r.pipeline_run_id = sa.pipeline_run_id WHERE {rfilter}
)
ORDER BY oe.created_at DESC
LIMIT 30;""",
    )
    q(
        "34",
        "Verificação: ausência de monthly_aggregation",
        "Busca atividades monthly_aggregation no caso anual direto.",
        "No cenário anual direto não deve haver agregação mensal.",
        "Nenhuma (resultado esperado: zero linhas).",
        f"""SELECT a.activity_id, a.name
FROM prov_core_prov_activity a
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rfilter}
  AND a.name LIKE '%monthly_aggregation%';""",
    )
    q(
        "35",
        "Verificação: ausência de annual_aggregation",
        "Busca atividades annual_aggregation no caso anual direto.",
        "Dado já é anual; não há rollup anual adicional.",
        "Nenhuma (resultado esperado: zero linhas).",
        f"""SELECT a.activity_id, a.name
FROM prov_core_prov_activity a
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {rfilter}
  AND a.name = 'annual_aggregation';""",
    )
    return s


def _final_lineage_annual(run: str) -> str:
    return f"""
-- ------------------------------------------------------------
-- Etapa 36 — Linhagem resumida ponta a ponta
-- ------------------------------------------------------------
-- O que esta query mostra:
-- Visão consolidada das principais etapas do caso anual direto.
--
-- Por que isso importa:
-- Fecha a narrativa da apresentação em uma única consulta.
--
-- Relações de proveniência demonstradas:
-- - Cadeia operacional + status de cada etapa
SELECT
    1 AS ordem_etapa,
    'pipeline_run' AS etapa_pipeline,
    r.run_code,
    r.reporting_period_reference AS periodo,
    'annual' AS granularidade,
    r.run_status AS status,
    'Início da linhagem' AS observacao
FROM pipeline_pipeline_run r
WHERE r.run_code = '{run}'
UNION ALL SELECT 2, 'source_artifact', sa.original_filename, r.reporting_period_reference, 'annual', 'received', sa.content_hash
FROM pipeline_source_artifact sa JOIN pipeline_pipeline_run r ON r.pipeline_run_id = sa.pipeline_run_id WHERE r.run_code = '{run}'
UNION ALL SELECT 3, 'wrapper_execution', we.wrapper_execution_id, r.reporting_period_reference, 'annual', we.execution_status, 'Transformação bruto→normalizado'
FROM pipeline_wrapper_execution we JOIN pipeline_pipeline_run r ON r.pipeline_run_id = we.pipeline_run_id WHERE r.run_code = '{run}'
UNION ALL SELECT 4, 'normalized_batch', nb.batch_code, r.reporting_period_reference, 'annual', 'generated', nb.content_hash
FROM pipeline_normalized_batch nb JOIN pipeline_pipeline_run r ON r.pipeline_run_id = nb.pipeline_run_id WHERE r.run_code = '{run}'
UNION ALL SELECT 5, 'semantic_integration', sie.semantic_integration_execution_id, r.reporting_period_reference, 'annual', sie.execution_status, 'Mapeamento ontológico'
FROM semantic_semantic_integration_execution sie JOIN pipeline_pipeline_run r ON r.pipeline_run_id = sie.pipeline_run_id WHERE r.run_code = '{run}'
UNION ALL SELECT 6, 'canonical_snapshot', cs.snapshot_label, r.reporting_period_reference, 'annual', 'published', cs.snapshot_hash
FROM semantic_canonical_snapshot cs JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cs.pipeline_run_id WHERE r.run_code = '{run}'
UNION ALL SELECT 7, 'calculation_execution', ce.calculation_execution_id, r.reporting_period_reference, 'annual', ce.execution_status, 'Cálculo sobre snapshot anual'
FROM calculation_calculation_execution ce JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ce.pipeline_run_id WHERE r.run_code = '{run}'
UNION ALL SELECT 8, 'result_set', rs.calculation_result_set_id, r.reporting_period_reference, 'annual', rs.result_set_status, 'Resultado + revisão + publicação'
FROM calculation_calculation_result_set rs JOIN pipeline_pipeline_run r ON r.pipeline_run_id = rs.pipeline_run_id WHERE r.run_code = '{run}'
UNION ALL SELECT 9, 'hash_record', hr.hash_record_id, r.reporting_period_reference, 'annual', hr.subject_kind, hr.hash_value
FROM audit_hash_record hr JOIN pipeline_pipeline_run r ON r.pipeline_run_id = hr.pipeline_run_id WHERE r.run_code = '{run}'
UNION ALL SELECT 10, 'blockchain_anchor', ba.blockchain_anchor_id, r.reporting_period_reference, 'annual', ba.anchor_status, ba.transaction_hash
FROM audit_blockchain_anchor ba JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ba.pipeline_run_id WHERE r.run_code = '{run}'
ORDER BY ordem_etapa;
"""


# Due to length, monthly and daily builders are in separate functions - continue in same file
def build_monthly_to_annual() -> str:
    farm = "Fazenda Boa Vista"
    annual_run = "demo_repo_boa_vista_2026-annual"
    monthly_filter = "r.farm_reference = 'Fazenda Boa Vista' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'"
    case_filter = "(r.run_code LIKE 'demo_repo_boa_vista_2026%' OR r.farm_reference = 'Fazenda Boa Vista')"
    parts = [
        header(
            2,
            "CASO 2: FAZENDA BOA VISTA — MENSAL PARA ANUAL",
            farm,
            "monthly → annual_aggregation → cálculo anual",
            "12 brutos mensais → … → 12 snapshots mensais → annual_aggregation → annual_aggregate → cálculo → publicação → hash → blockchain",
            "queries_02_monthly_to_annual_pipeline.sql",
        ),
    ]
    parts.extend(_monthly_steps(monthly_filter, annual_run, farm))
    parts.append(prov_section(case_filter))
    parts.append(_final_lineage_monthly(annual_run, farm))
    return "\n".join(parts)


def _monthly_steps(monthly_filter: str, annual_run: str, farm: str) -> list[str]:
    s: list[str] = []

    def q(step, title, shows, why, prov, sql):
        s.append(block(step, title, shows, why, prov, sql))

    q("1", "Pipeline runs do caso", f"Runs mensais e run anual {annual_run}.", "Mapa de execuções do cenário.", "pipeline_run.", f"""SELECT r.pipeline_run_id, r.run_code, r.reporting_period_reference, r.run_status, r.started_at
FROM pipeline_pipeline_run r
WHERE r.farm_reference = '{farm}' AND r.run_code LIKE 'demo_repo_boa_vista_2026%'
ORDER BY r.reporting_period_reference;""")

    q("2", "Bundles", "Bundles por run do caso.", "Organização PROV.", "prov_bundle.", f"""SELECT r.run_code, b.bundle_type, b.status, b.created_at
FROM prov_core_prov_bundle b
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = b.pipeline_run_id
WHERE r.farm_reference = '{farm}' AND r.run_code LIKE 'demo_repo_boa_vista_2026%'
ORDER BY r.run_code, b.bundle_type;""")

    q("3", "Agentes", "Agentes trigger e revisor.", "Responsabilidade.", "associated_with.", """SELECT agent_id, agent_type, name, external_reference FROM prov_core_prov_agent
WHERE external_reference LIKE 'demo:%';""")

    q("4", "12 source artifacts mensais", "Um artefato bruto por mês.", "Entradas da agregação anual.", "source_artifact.", f"""SELECT r.run_code, r.reporting_period_reference, sa.source_artifact_id, sa.original_filename, sa.content_hash
FROM pipeline_source_artifact sa
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = sa.pipeline_run_id
WHERE {monthly_filter}
ORDER BY r.reporting_period_reference;""")

    for step, tbl, alias, extra in [
        ("5", "pipeline_wrapper_execution", "we", "wrapper_execution_id, execution_status"),
        ("6", "pipeline_normalized_batch", "nb", "batch_code, record_count, content_hash"),
        ("7", "semantic_semantic_integration_execution", "sie", "ontology_name, execution_status"),
        ("8", "semantic_canonical_snapshot", "cs", "snapshot_label, snapshot_hash"),
    ]:
        q(step, f"{tbl} mensais", f"Registros mensais em {tbl}.", "Etapas repetidas 12 vezes.", "used/generated por mês.", f"""SELECT r.run_code, r.reporting_period_reference, {alias}.*
FROM {tbl} {alias}
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = {alias}.pipeline_run_id
WHERE {monthly_filter}
ORDER BY r.reporting_period_reference;""".replace(f"{alias}.*", extra if "." not in extra else extra))

    # Fix steps 5-8 with proper column lists
    s[-4] = block("5", "12 wrapper executions mensais", "Execução de wrapper por mês.", "Transformação mensal.", "used/generated.", f"""SELECT r.run_code, we.wrapper_execution_id, we.execution_status, we.prov_activity_id
FROM pipeline_wrapper_execution we JOIN pipeline_pipeline_run r ON r.pipeline_run_id = we.pipeline_run_id
WHERE {monthly_filter} ORDER BY r.reporting_period_reference;""")

    s[-3] = block("6", "12 normalized batches mensais", "Lotes normalizados mensais.", "Insumo semântico mensal.", "derived_from.", f"""SELECT r.run_code, nb.batch_code, nb.record_count, nb.content_hash
FROM pipeline_normalized_batch nb JOIN pipeline_pipeline_run r ON r.pipeline_run_id = nb.pipeline_run_id
WHERE {monthly_filter} ORDER BY r.reporting_period_reference;""")

    s[-2] = block("7", "12 semantic integrations mensais", "Integrações semânticas mensais.", "Mapeamento mensal.", "semantic_integration.", f"""SELECT r.run_code, sie.semantic_integration_execution_id, sie.execution_status
FROM semantic_semantic_integration_execution sie JOIN pipeline_pipeline_run r ON r.pipeline_run_id = sie.pipeline_run_id
WHERE {monthly_filter} ORDER BY r.reporting_period_reference;""")

    s[-1] = block("8", "12 canonical snapshots mensais", "Snapshots canônicos mensais.", "Entradas da annual_aggregation.", "canonical_snapshot.", f"""SELECT r.run_code, cs.canonical_snapshot_id, cs.snapshot_label, cs.prov_entity_id
FROM semantic_canonical_snapshot cs JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE {monthly_filter} ORDER BY r.reporting_period_reference;""")

    q("9", "Canonical snapshot items mensais", "Itens dos snapshots mensais.", "Detalhe por métrica.", "snapshot_item.", f"""SELECT r.run_code, csi.item_key, csi.payload
FROM semantic_canonical_snapshot_item csi
JOIN semantic_canonical_snapshot cs ON cs.canonical_snapshot_id = csi.canonical_snapshot_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cs.pipeline_run_id
WHERE {monthly_filter}
ORDER BY r.run_code, csi.item_key;""")

    q("10", "Ontology links mensais", "Publicação canônica mensal.", "Vínculo ontológico.", "ontology_resource_link.", f"""SELECT r.run_code, orl.ontology_uri, orl.publication_stage
FROM semantic_ontology_resource_link orl JOIN pipeline_pipeline_run r ON r.pipeline_run_id = orl.pipeline_run_id
WHERE {monthly_filter};""")

    q("11", "PROV: wrappers usaram source artifacts", "Used mensais wrapper→bruto.", "12 consumos explícitos.", "prov_used.", f"""SELECT r.run_code, u.role, e.name AS entidade_usada
FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = u.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {monthly_filter} AND a.activity_type = 'wrapper_execution'
ORDER BY r.run_code;""")

    q("12", "PROV: wrappers geraram normalized batches", "Generated mensais.", "12 produções.", "prov_generated.", f"""SELECT r.run_code, e.name AS entidade_gerada
FROM prov_core_prov_generated g
JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = g.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {monthly_filter} AND a.activity_type = 'wrapper_execution'
ORDER BY r.run_code;""")

    q("13", "PROV: integrações usaram normalized batches", "Used integração→batch.", "Ligação semântica.", "prov_used.", f"""SELECT r.run_code, e.name
FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = u.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {monthly_filter} AND a.activity_type = 'semantic_integration'
ORDER BY r.run_code;""")

    q("14", "PROV: integrações geraram snapshots mensais", "Generated integração→snapshot.", "12 snapshots.", "prov_generated.", f"""SELECT r.run_code, e.name
FROM prov_core_prov_generated g
JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = g.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {monthly_filter} AND a.activity_type = 'semantic_integration'
ORDER BY r.run_code;""")

    q("15", "Atividade annual_aggregation", "Atividade de agregação anual.", "Consolida 12 meses.", "prov_activity OTHER name=annual_aggregation.", f"""SELECT a.activity_id, a.name, a.status, a.started_at, a.ended_at
FROM prov_core_prov_activity a
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = '{annual_run}' AND a.name = 'annual_aggregation';""")

    q("16", "12 entradas used pela annual_aggregation", "Snapshots mensais consumidos.", "Cardinalidade da agregação.", "prov_used role=aggregation_input.", f"""SELECT u.used_id, se.name AS snapshot_mensal_fonte, u.used_at
FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN prov_core_prov_entity se ON se.entity_id = u.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = '{annual_run}' AND a.name = 'annual_aggregation'
ORDER BY u.used_at;""")

    q("17", "Entidade annual_aggregate", "Entidade agregada anual.", "Produto da agregação.", "entity_kind annual-aggregation.", f"""SELECT e.entity_id, e.entity_kind, e.name, e.content_hash, e.metadata
FROM prov_core_prov_entity e
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = e.pipeline_run_id
WHERE r.run_code = '{annual_run}' AND e.entity_kind = 'annual-aggregation';""")

    q("18", "PROV: annual_aggregate gerado pela agregação", "Generated da annual_aggregation.", "Saída da atividade.", "prov_generated.", f"""SELECT g.generated_id, e.name
FROM prov_core_prov_generated g
JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = g.entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = '{annual_run}' AND a.name = 'annual_aggregation';""")

    q("19", "PROV: annual_aggregate deriva dos 12 meses", "Derived_from agregado←mensais.", "Linhagem rollup.", "prov_derived_from derivation_type=annual_aggregation.", f"""SELECT d.derived_id, se.name AS fonte_mensal, ge.name AS agregado
FROM prov_core_prov_derived_from d
JOIN prov_core_prov_entity ge ON ge.entity_id = d.generated_entity_id
JOIN prov_core_prov_entity se ON se.entity_id = d.source_entity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ge.pipeline_run_id
WHERE r.run_code = '{annual_run}' AND d.derivation_type = 'annual_aggregation'
ORDER BY se.name;""")

    q("20", "Total anual esperado (150500 litros)", "Soma do resultado agregado.", "Validação de negócio.", "calculation_result_item.", f"""SELECT ri.result_name, ri.result_value, ri.result_unit
FROM calculation_calculation_result_item ri
JOIN calculation_calculation_result_set rs ON rs.calculation_result_set_id = ri.calculation_result_set_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = rs.pipeline_run_id
WHERE r.run_code = '{annual_run}' AND ri.result_name = 'aggregated_milk_production';""")

    # calculation 21-31 on annual run
    ar = f"r.run_code = '{annual_run}'"
    for step, title, sql in [
        ("21", "Calculation method", "SELECT method_code, method_name FROM calculation_calculation_method WHERE method_code = 'demo-repo-ghg-2026';"),
        ("22", "Method version", """SELECT cmv.version_label, cmv.status FROM calculation_calculation_method_version cmv
JOIN calculation_calculation_method cm ON cm.calculation_method_id = cmv.calculation_method_id WHERE cm.method_code = 'demo-repo-ghg-2026';"""),
        ("23", "Parameter set", f"SELECT calculation_parameter_set_id, parameter_set_status FROM calculation_calculation_parameter_set cps JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cps.pipeline_run_id WHERE {ar};"),
        ("24", "Parameter values", f"SELECT cpv.parameter_name, cpv.parameter_value_numeric FROM calculation_calculation_parameter_value cpv JOIN calculation_calculation_parameter_set cps ON cps.calculation_parameter_set_id = cpv.calculation_parameter_set_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cps.pipeline_run_id WHERE {ar};"),
        ("25", "Calculation execution", f"SELECT calculation_execution_id, canonical_snapshot_id FROM calculation_calculation_execution ce JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ce.pipeline_run_id WHERE {ar};"),
    ]:
        q(step, title, f"{title} no run anual.", "Cálculo sobre agregado.", "used snapshot agregado.", sql)

    q("26", "PROV: cálculo usou snapshot/agregado anual", "Used do calculation_execution.", "Entrada é agregado, não 12 meses.", "prov_used.", f"""SELECT u.used_id, e.name, e.entity_type
FROM prov_core_prov_used u JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN prov_core_prov_entity e ON e.entity_id = u.entity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE {ar} AND a.activity_type = 'calculation_execution';""")

    q("27", "Result set preliminar", "Resultado do cálculo anual.", "Saída agregada.", "generated.", f"SELECT result_set_status, generated_at FROM calculation_calculation_result_set rs JOIN pipeline_pipeline_run r ON r.pipeline_run_id = rs.pipeline_run_id WHERE {ar};")
    q("28", "Result items", "Itens de resultado.", "Métricas.", "result_item.", f"SELECT result_name, result_value, result_unit FROM calculation_calculation_result_item ri JOIN calculation_calculation_result_set rs ON rs.calculation_result_set_id = ri.calculation_result_set_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = rs.pipeline_run_id WHERE {ar};")
    q("29", "PROV: resultado gerado pelo cálculo", "Generated cálculo→result.", "Produção.", "prov_generated.", f"""SELECT g.generated_id, e.name FROM prov_core_prov_generated g JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id JOIN prov_core_prov_entity e ON e.entity_id = g.entity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE {ar} AND a.activity_type = 'calculation_execution';""")
    q("30", "Review aprovada", "Aprovação humana.", "Governança.", "review + associated_with.", f"SELECT decision, review_comment FROM calculation_calculation_review cr JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cr.pipeline_run_id WHERE {ar};")
    q("31", "Publicação final", "Result publication.", "Publicação.", "result_publication.", f"SELECT publication_status, published_at FROM calculation_result_publication_execution pe JOIN pipeline_pipeline_run r ON r.pipeline_run_id = pe.pipeline_run_id WHERE {ar};")
    q("32", "Hashes", "Hashes do run anual.", "Integridade.", "hash_record.", f"SELECT subject_kind, hash_value FROM audit_hash_record hr JOIN pipeline_pipeline_run r ON r.pipeline_run_id = hr.pipeline_run_id WHERE {ar};")
    q("33", "Blockchain anchors", "Ancoragens simuladas.", "Demo chain.", "blockchain_anchor.", f"SELECT transaction_hash, anchor_status FROM audit_blockchain_anchor ba JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ba.pipeline_run_id WHERE {ar};")
    q("34", "Audit events", "Eventos de auditoria.", "Trilha.", "audit_event.", "SELECT event_type, recorded_at FROM audit_audit_event WHERE event_type LIKE 'demo.%' ORDER BY recorded_at DESC LIMIT 20;")
    q("35", "Outbox events", "Outbox.", "Integração.", "outbox.", f"SELECT event_type, status FROM audit_outbox_event ORDER BY created_at DESC LIMIT 20;")

    q("36", "Verificação: annual_aggregation com 12 entradas", "Contagem de used na agregação.", "Deve ser 12.", "prov_used count.", f"""SELECT COUNT(u.used_id) AS entradas_mensais
FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id
WHERE r.run_code = '{annual_run}' AND a.name = 'annual_aggregation';""")

    q("37", "Verificação: existe annual_aggregate", "Entidade agregada presente.", "Produto da agregação.", "entity_kind.", f"""SELECT entity_id, entity_kind FROM prov_core_prov_entity e JOIN pipeline_pipeline_run r ON r.pipeline_run_id = e.pipeline_run_id WHERE r.run_code = '{annual_run}' AND e.entity_kind = 'annual-aggregation';""")

    q("38", "Verificação: cálculo usa agregado (não 12 meses direto)", "Cálculo no run anual com 1 snapshot agregado.", "Não há 12 calculation_executions mensais para o total anual.", "canonical_snapshot no run anual.", f"""SELECT COUNT(*) AS execucoes_calculo_run_anual
FROM calculation_calculation_execution ce JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ce.pipeline_run_id WHERE r.run_code = '{annual_run}';""")

    return s


def _final_lineage_monthly(annual_run: str, farm: str) -> str:
    return block(
        "39",
        "Linhagem resumida mensal → anual",
        "Narrativa consolidada: 12 meses → agregação → cálculo → publicação → hash.",
        "Fechamento da apresentação.",
        "derived_from + used + generated.",
        f"""SELECT 'mensal' AS fase, COUNT(*) AS qtd_runs
FROM pipeline_pipeline_run r WHERE r.farm_reference = '{farm}' AND r.run_code LIKE 'demo_repo_boa_vista_2026-%' AND r.run_code NOT LIKE '%-annual'
UNION ALL SELECT 'annual_aggregation', COUNT(*) FROM prov_core_prov_activity a
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{annual_run}' AND a.name = 'annual_aggregation'
UNION ALL SELECT 'entradas_agregacao', COUNT(*) FROM prov_core_prov_used u
JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{annual_run}' AND a.name = 'annual_aggregation'
UNION ALL SELECT 'publicacao_anual', COUNT(*) FROM calculation_result_publication_execution pe
JOIN pipeline_pipeline_run r ON r.pipeline_run_id = pe.pipeline_run_id WHERE r.run_code = '{annual_run}';""",
    )


def build_daily_monthly_annual() -> str:
    farm = "Fazenda Santa Clara"
    jan_daily = "r.farm_reference = 'Fazenda Santa Clara' AND r.run_code LIKE 'demo_repo_santa_clara_2026-01-%' AND r.run_code NOT LIKE '%-agg%'"
    monthly_agg = "r.farm_reference = 'Fazenda Santa Clara' AND r.run_code LIKE 'demo_repo_santa_clara_2026-m%'"
    annual_run = "demo_repo_santa_clara_2026-annual"
    jan_agg_run = "demo_repo_santa_clara_2026-m01-agg"
    case_filter = "r.farm_reference = 'Fazenda Santa Clara' AND r.run_code LIKE 'demo_repo_santa_clara_2026%'"
    parts = [
        header(
            3,
            "CASO 3: FAZENDA SANTA CLARA — DIÁRIO PARA MENSAL E ANUAL",
            farm,
            "daily (jan) → monthly_aggregation_january → 12 monthly → annual_aggregation",
            "31 diários → agregado jan → 12 mensais → agregado anual → cálculo → publicação → hash",
            "queries_03_daily_to_monthly_to_annual_pipeline.sql",
        ),
    ]
    parts.extend(_daily_steps(jan_daily, monthly_agg, jan_agg_run, annual_run, farm))
    parts.append(prov_section(case_filter))
    parts.append(
        block(
            "42",
            "Linhagem resumida diário → mensal → anual",
            "Contagens das fases do caso Santa Clara.",
            "Fechamento da apresentação.",
            "used + derived_from em duas agregações.",
            f"""SELECT 'diarios_janeiro' AS fase, COUNT(*) AS qtd
FROM pipeline_pipeline_run r WHERE {jan_daily}
UNION ALL SELECT 'monthly_agg_jan', COUNT(*) FROM prov_core_prov_activity a JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{jan_agg_run}' AND a.name = 'monthly_aggregation_january'
UNION ALL SELECT 'entradas_diarias_na_agreg_jan', COUNT(*) FROM prov_core_prov_used u JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{jan_agg_run}' AND a.name = 'monthly_aggregation_january'
UNION ALL SELECT 'runs_mensais_representativos', COUNT(*) FROM pipeline_pipeline_run r WHERE r.farm_reference = '{farm}' AND r.run_code LIKE 'demo_repo_santa_clara_2026-m%'
UNION ALL SELECT 'entradas_na_agreg_anual', COUNT(*) FROM prov_core_prov_used u JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{annual_run}' AND a.name = 'annual_aggregation';""",
        )
    )
    return "\n".join(parts)


def _daily_steps(jan_daily, monthly_agg, jan_agg_run, annual_run, farm) -> list[str]:
    s: list[str] = []

    def q(step, title, shows, why, prov, sql):
        s.append(block(step, title, shows, why, prov, sql))

    q("1", "Pipeline runs Santa Clara", "Runs diários, mensais e anual.", "Mapa do caso.", "pipeline_run.", f"""SELECT run_code, reporting_period_reference, run_status FROM pipeline_pipeline_run r
WHERE r.farm_reference = '{farm}' AND r.run_code LIKE 'demo_repo_santa_clara_2026%' ORDER BY reporting_period_reference;""")

    q("2", "Bundles", "Bundles do caso.", "Organização PROV.", "prov_bundle.", f"""SELECT r.run_code, b.bundle_type, b.status FROM prov_core_prov_bundle b JOIN pipeline_pipeline_run r ON r.pipeline_run_id = b.pipeline_run_id
WHERE r.farm_reference = '{farm}' AND r.run_code LIKE 'demo_repo_santa_clara_2026%' ORDER BY r.run_code;""")

    q("3", "Agentes", "Agentes do demo.", "Responsabilidade.", "agents.", "SELECT name, agent_type, external_reference FROM prov_core_prov_agent WHERE external_reference LIKE 'demo:%';")

    q("4", "31 source artifacts diários (janeiro)", "Um bruto por dia.", "Base da agregação mensal de janeiro.", "source_artifact.", f"""SELECT r.run_code, sa.original_filename, sa.content_hash FROM pipeline_source_artifact sa JOIN pipeline_pipeline_run r ON r.pipeline_run_id = sa.pipeline_run_id WHERE {jan_daily} ORDER BY r.run_code;""")

    q("5", "31 wrapper executions diárias", "Wrappers por dia.", "Transformação diária.", "wrapper_execution.", f"""SELECT r.run_code, we.wrapper_execution_id, we.execution_status FROM pipeline_wrapper_execution we JOIN pipeline_pipeline_run r ON r.pipeline_run_id = we.pipeline_run_id WHERE {jan_daily} ORDER BY r.run_code;""")

    q("6", "31 normalized batches diários", "Lotes diários.", "Insumo semântico diário.", "normalized_batch.", f"""SELECT r.run_code, nb.batch_code, nb.record_count FROM pipeline_normalized_batch nb JOIN pipeline_pipeline_run r ON r.pipeline_run_id = nb.pipeline_run_id WHERE {jan_daily} ORDER BY r.run_code;""")

    q("7", "31 semantic integrations diárias", "Integrações diárias.", "Mapeamento diário.", "semantic_integration.", f"""SELECT r.run_code, sie.semantic_integration_execution_id FROM semantic_semantic_integration_execution sie JOIN pipeline_pipeline_run r ON r.pipeline_run_id = sie.pipeline_run_id WHERE {jan_daily} ORDER BY r.run_code;""")

    q("8", "31 canonical snapshots diários", "Snapshots diários.", "Entradas da agregação de janeiro.", "canonical_snapshot.", f"""SELECT r.run_code, cs.canonical_snapshot_id, cs.prov_entity_id FROM semantic_canonical_snapshot cs JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cs.pipeline_run_id WHERE {jan_daily} ORDER BY r.run_code;""")

    q("9", "Snapshot items diários", "Itens diários.", "Detalhe.", "snapshot_item.", f"""SELECT r.run_code, csi.item_key FROM semantic_canonical_snapshot_item csi JOIN semantic_canonical_snapshot cs ON cs.canonical_snapshot_id = csi.canonical_snapshot_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cs.pipeline_run_id WHERE {jan_daily} ORDER BY r.run_code LIMIT 50;""")

    q("10", "Ontology links diários", "Links canônicos diários.", "Publicação canônica.", "ontology_resource_link.", f"""SELECT r.run_code, orl.ontology_uri FROM semantic_ontology_resource_link orl JOIN pipeline_pipeline_run r ON r.pipeline_run_id = orl.pipeline_run_id WHERE {jan_daily} ORDER BY r.run_code LIMIT 20;""")

    q("11", "PROV: wrappers usaram bruto diário", "Used diários.", "31 consumos.", "prov_used.", f"""SELECT COUNT(*) AS qtd_used_wrapper FROM prov_core_prov_used u JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE {jan_daily} AND a.activity_type = 'wrapper_execution';""")

    q("12", "PROV: wrappers geraram batch diário", "Generated diários.", "31 produções.", "prov_generated.", f"""SELECT COUNT(*) AS qtd_generated_batch FROM prov_core_prov_generated g JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE {jan_daily} AND a.activity_type = 'wrapper_execution';""")

    q("13", "PROV: integração usou batch diário", "Used integração diária.", "Ligação semântica.", "prov_used.", f"""SELECT COUNT(*) FROM prov_core_prov_used u JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE {jan_daily} AND a.activity_type = 'semantic_integration';""")

    q("14", "PROV: integração gerou canônico diário", "Generated snapshot diário.", "Saída semântica.", "prov_generated.", f"""SELECT COUNT(*) FROM prov_core_prov_generated g JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE {jan_daily} AND a.activity_type = 'semantic_integration';""")

    q("15", "Atividade monthly_aggregation_january", "Agregação mensal de janeiro.", "Consolida 31 dias.", "activity name=monthly_aggregation_january.", f"""SELECT a.activity_id, a.name, a.started_at FROM prov_core_prov_activity a JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{jan_agg_run}' AND a.name = 'monthly_aggregation_january';""")

    q("16", "31 entradas na monthly_aggregation_january", "Used diários na agregação jan.", "Cardinalidade 31.", "prov_used.", f"""SELECT COUNT(u.used_id) AS entradas_diarias FROM prov_core_prov_used u JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{jan_agg_run}' AND a.name = 'monthly_aggregation_january';""")

    q("17", "Entidade monthly_aggregate_january", "Agregado mensal de janeiro.", "Produto intermediário.", "entity_kind monthly-aggregation-january.", f"""SELECT e.entity_id, e.entity_kind, e.name FROM prov_core_prov_entity e JOIN pipeline_pipeline_run r ON r.pipeline_run_id = e.pipeline_run_id WHERE r.run_code = '{jan_agg_run}' AND e.entity_kind = 'monthly-aggregation-january';""")

    q("18", "PROV: monthly_aggregate gerado", "Generated agregação jan.", "Saída jan.", "prov_generated.", f"""SELECT g.generated_id, e.name FROM prov_core_prov_generated g JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id JOIN prov_core_prov_entity e ON e.entity_id = g.entity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{jan_agg_run}' AND a.name = 'monthly_aggregation_january';""")

    q("19", "PROV: monthly_aggregate deriva de 31 dias", "Derived_from diário→mensal jan.", "Linhagem jan.", "prov_derived_from.", f"""SELECT COUNT(*) AS derivacoes_diarias FROM prov_core_prov_derived_from d JOIN prov_core_prov_entity ge ON ge.entity_id = d.generated_entity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ge.pipeline_run_id WHERE r.run_code = '{jan_agg_run}' AND d.derivation_type = 'monthly_aggregation_january';""")

    q("20", "12 monthly aggregates (runs m01..m12)", "Representação mensal fev-dez + jan agregado.", "Entradas da agregação anual.", "canonical snapshots em runs m*-agg.", f"""SELECT r.run_code, cs.snapshot_label FROM semantic_canonical_snapshot cs JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cs.pipeline_run_id WHERE {monthly_agg} ORDER BY r.run_code;""")

    q("21", "Atividade annual_aggregation", "Agregação anual.", "Consolida 12 meses.", "annual_aggregation.", f"""SELECT a.activity_id, a.name FROM prov_core_prov_activity a JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{annual_run}' AND a.name = 'annual_aggregation';""")

    q("22", "12 entradas na annual_aggregation", "Used mensais na agregação anual.", "Cardinalidade 12.", "prov_used.", f"""SELECT COUNT(u.used_id) AS entradas_mensais FROM prov_core_prov_used u JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{annual_run}' AND a.name = 'annual_aggregation';""")

    q("23", "Entidade annual_aggregate", "Agregado anual.", "Entrada do cálculo.", "annual-aggregation.", f"""SELECT e.entity_id, e.entity_kind FROM prov_core_prov_entity e JOIN pipeline_pipeline_run r ON r.pipeline_run_id = e.pipeline_run_id WHERE r.run_code = '{annual_run}' AND e.entity_kind = 'annual-aggregation';""")

    q("24", "PROV: annual_aggregate gerado", "Generated anual.", "Saída anual.", "prov_generated.", f"""SELECT g.generated_id FROM prov_core_prov_generated g JOIN prov_core_prov_activity a ON a.activity_id = g.activity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{annual_run}' AND a.name = 'annual_aggregation';""")

    q("25", "PROV: annual_aggregate deriva de 12 meses", "Derived_from mensal→anual.", "Linhagem anual.", "prov_derived_from.", f"""SELECT COUNT(*) FROM prov_core_prov_derived_from d JOIN prov_core_prov_entity ge ON ge.entity_id = d.generated_entity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ge.pipeline_run_id WHERE r.run_code = '{annual_run}' AND d.derivation_type = 'annual_aggregation';""")

    ar = f"r.run_code = '{annual_run}'"
    q("26", "Calculation method", "Método.", "Catálogo.", "method.", "SELECT method_code, method_name FROM calculation_calculation_method WHERE method_code = 'demo-repo-ghg-2026';")
    q("27", "Method version", "Versão.", "Catálogo.", "version.", "SELECT version_label, status FROM calculation_calculation_method_version cmv JOIN calculation_calculation_method cm ON cm.calculation_method_id = cmv.calculation_method_id WHERE cm.method_code = 'demo-repo-ghg-2026';")
    q("28", "Parameter set", "Parâmetros.", "Execução.", "parameter_set.", f"SELECT calculation_parameter_set_id FROM calculation_calculation_parameter_set cps JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cps.pipeline_run_id WHERE {ar};")
    q("29", "Parameter values", "Valores.", "Execução.", "parameter_value.", f"SELECT parameter_name, parameter_value_numeric FROM calculation_calculation_parameter_value cpv JOIN calculation_calculation_parameter_set cps ON cps.calculation_parameter_set_id = cpv.calculation_parameter_set_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cps.pipeline_run_id WHERE {ar};")
    q("30", "Calculation execution", "Execução.", "Sobre agregado anual.", "calculation_execution.", f"SELECT calculation_execution_id, canonical_snapshot_id FROM calculation_calculation_execution ce JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ce.pipeline_run_id WHERE {ar};")
    q("31", "PROV: cálculo usou annual_aggregate", "Used cálculo.", "Não usa 31 dias direto.", "prov_used.", f"""SELECT e.name, e.entity_type FROM prov_core_prov_used u JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id JOIN prov_core_prov_entity e ON e.entity_id = u.entity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE {ar} AND a.activity_type = 'calculation_execution';""")
    q("32", "Result set", "Resultado.", "Saída.", "result_set.", f"SELECT result_set_status FROM calculation_calculation_result_set rs JOIN pipeline_pipeline_run r ON r.pipeline_run_id = rs.pipeline_run_id WHERE {ar};")
    q("33", "Result items", "Itens.", "Métricas.", "result_item.", f"SELECT result_name, result_value FROM calculation_calculation_result_item ri JOIN calculation_calculation_result_set rs ON rs.calculation_result_set_id = ri.calculation_result_set_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = rs.pipeline_run_id WHERE {ar};")
    q("34", "Review", "Aprovação.", "Governança.", "review.", f"SELECT decision FROM calculation_calculation_review cr JOIN pipeline_pipeline_run r ON r.pipeline_run_id = cr.pipeline_run_id WHERE {ar};")
    q("35", "Publication", "Publicação.", "Final.", "publication.", f"SELECT publication_status FROM calculation_result_publication_execution pe JOIN pipeline_pipeline_run r ON r.pipeline_run_id = pe.pipeline_run_id WHERE {ar};")
    q("36", "Hashes", "Hashes.", "Integridade.", "hash.", f"SELECT subject_kind, hash_value FROM audit_hash_record hr JOIN pipeline_pipeline_run r ON r.pipeline_run_id = hr.pipeline_run_id WHERE {ar};")
    q("37", "Blockchain", "Anchors.", "Simulado.", "anchor.", f"SELECT transaction_hash, anchor_status FROM audit_blockchain_anchor ba JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ba.pipeline_run_id WHERE {ar};")
    q("38", "Audit events", "Auditoria.", "Eventos.", "audit.", "SELECT event_type FROM audit_audit_event WHERE event_type LIKE 'demo.%' LIMIT 15;")
    q("39", "Verificação: monthly_aggregation_january com 31 entradas", "Contagem 31.", "Deve retornar 31.", "count used.", f"""SELECT COUNT(u.used_id) AS deve_ser_31 FROM prov_core_prov_used u JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{jan_agg_run}' AND a.name = 'monthly_aggregation_january';""")
    q("40", "Verificação: annual_aggregation com 12 entradas", "Contagem 12.", "Deve retornar 12.", "count used.", f"""SELECT COUNT(u.used_id) AS deve_ser_12 FROM prov_core_prov_used u JOIN prov_core_prov_activity a ON a.activity_id = u.activity_id JOIN pipeline_pipeline_run r ON r.pipeline_run_id = a.pipeline_run_id WHERE r.run_code = '{annual_run}' AND a.name = 'annual_aggregation';""")
    q("41", "Verificação: cálculo usa annual_aggregate", "1 execução no run anual.", "Entrada agregada.", "calculation on annual run.", f"SELECT COUNT(*) AS execucoes FROM calculation_calculation_execution ce JOIN pipeline_pipeline_run r ON r.pipeline_run_id = ce.pipeline_run_id WHERE {ar};""")

    return s


def main() -> None:
    files = {
        "queries_01_annual_direct_pipeline.sql": build_annual_direct(),
        "queries_02_monthly_to_annual_pipeline.sql": build_monthly_to_annual(),
        "queries_03_daily_to_monthly_to_annual_pipeline.sql": build_daily_monthly_annual(),
    }
    for name, content in files.items():
        path = OUT / name
        path.write_text(content.strip() + "\n", encoding="utf-8")
        print(f"Wrote {path} ({content.count('SELECT')} SELECT blocks approx)")


if __name__ == "__main__":
    main()
