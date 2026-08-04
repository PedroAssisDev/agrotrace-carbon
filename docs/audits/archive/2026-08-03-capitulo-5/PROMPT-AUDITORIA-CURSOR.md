# PAPEL

Atue simultaneamente como:

- engenheiro de requisitos;
- arquiteto de software;
- revisor de código;
- especialista em frontend;
- analista de testes;
- auditor de qualidade;
- pesquisador responsável por produzir evidências técnicas para uma dissertação de mestrado.

Seja rigoroso, conservador e orientado por evidências. Não presuma conformidade. Prefira “não verificável” a afirmações sem comprovação.

# MISSÃO

Analisar o repositório completo do protótipo acadêmico AgroTrace Carbon / arquitetura de MRV agropecuário (terceiro ciclo) e determinar, para cada requisito da dissertação listado neste prompt, se o projeto está:

- **Atendido**;
- **Parcialmente atendido**;
- **Não atendido**;
- **Não aplicável**;
- **Não verificável com as evidências disponíveis**.

Um requisito **não** pode ser considerado atendido apenas porque existe arquivo, componente, rota ou função com nome relacionado. Toda conclusão deve estar sustentada por implementação, comportamento executado, teste ou outra evidência verificável.

# REGRA CENTRAL DE CONFIABILIDADE

> **Não presuma conformidade. Não invente implementação, execução, teste, arquivo, resultado, métrica ou evidência. Quando não houver comprovação suficiente, utilize “parcialmente atendido”, “não atendido” ou “não verificável”, conforme o caso. Toda afirmação relevante deve ser rastreável até um arquivo, símbolo, comando, resultado de teste, comportamento observado ou evidência documentada.**

Diferencie explicitamente em todo o relatório:

1. **requisito declarado na dissertação**;
2. **critério inferido diretamente a partir do requisito** (para torná-lo verificável);
3. **recomendação técnica complementar** (não altera a classificação acadêmica, salvo quando o próprio requisito exigir aquela característica).

# CONTEXTO DA DISSERTAÇÃO

## Identificação

- **Autor:** Pedro Henrique Assis Silva
- **Instituição:** Universidade Federal de Juiz de Fora — Programa de Pós-Graduação em Ciência da Computação
- **Título:** Arquitetura Orientada ao Ciclo de Vida de Dados Agropecuários para Monitoramento, Relato e Verificação de Emissões de Gases de Efeito Estufa
- **Orientador:** Prof. José Maria Nazar David, Dr.
- **Coorientadores:** Prof.ª Regina Maria Maciel Braga, Dra.; Prof. Wagner Antonio Arbex, Dr.
- **Ano:** 2026
- **Artefato avaliado:** terceiro ciclo da pesquisa (arquitetura de MRV agropecuário), evolução do CarbonSECO for Livestock
- **Metodologia:** Design Science Research (DSR)

## Tema

Arquitetura computacional para apoiar o ciclo de vida de dados agropecuários em processos de MRV (Monitoramento, Relato e Verificação) de emissões de gases de efeito estufa, integrando preservação de dados brutos, wrappers, normalização, validação, ontologia AgroMRV-Lite, cálculo de emissões, métricas, predição, proveniência, revisão humana, publicação controlada, pacote de evidências, hashes/Merkle, ancoragem em blockchain (simulada e EVM) e verificação.

## Problema / motivação

Processos de MRV agropecuário exigem que resultados de emissão sejam compreendidos como produtos de um fluxo de dados, e não apenas como valores finais. Dados heterogêneos (formatos, unidades, granularidades temporal e organizacional: animal, lote, propriedade; diário, mensal, anual) precisam ser preservados, extraídos, normalizados, validados, representados semanticamente e vinculados a período e unidade de análise. Sem registro das etapas, o resultado fica desconectado da origem, dificultando revisão técnica, auditoria e reprodução. Os dois primeiros ciclos trataram cálculo/ontologia/predição, mas não o ciclo de vida completo com revisão, publicação e evidências auditáveis.

## Questões de pesquisa

- **QP:** Como estruturar uma arquitetura computacional para apoiar o ciclo de vida de dados agropecuários em processos de MRV de emissões de gases de efeito estufa?
- **QP1:** Como integrar, normalizar e representar semanticamente dados agropecuários heterogêneos, considerando diferentes granularidades temporais e organizacionais?
- **QP2:** Como executar cálculos e métricas de emissões agropecuárias e disponibilizar predições de emissões e produção, preservando a distinção entre resultados calculados, resultados aprovados, resultados publicados e estimativas preditivas?
- **QP3:** Como registrar a proveniência, apoiar a auditoria técnica e ancorar evidências de resultados publicados em uma arquitetura de MRV agropecuário?

## Objetivo geral

Propor, desenvolver e avaliar uma arquitetura computacional para apoiar o ciclo de vida de dados agropecuários em processos de MRV, integrando dados heterogêneos, representação semântica, cálculo de emissões, métricas, predição, proveniência, revisão humana, publicação controlada, auditoria técnica, ancoragem e verificação de evidências.

## Objetivos específicos

a) especificar uma arquitetura orientada ao ciclo de vida de dados agropecuários e à governança dos resultados de MRV;
b) integrar, em uma pipeline unificada, os serviços dos ciclos anteriores do CarbonSECO for Livestock e fontes heterogêneas;
c) representar semanticamente os dados e sua granularidade (temporal e organizacional);
d) implementar cálculo de emissões, métricas, predição, geração determinística de evidências, ancoragem criptográfica em blockchain e consulta dos registros;
e) registrar proveniência das etapas do ciclo (entrada até verificação);
f) diferenciar resultado preliminar, aprovado e publicado, com revisão humana antes da publicação final;
g) disponibilizar interfaces de visualização e auditoria técnica;
h) avaliar a arquitetura em cenários representativos (diferentes granularidades e estados do ciclo).

## Usuários / atores

- **Ator principal declarado:** usuário responsável (revisão, aprovação, acompanhamento, auditoria).
- **Papéis típicos de proveniência (PROV):** executor, integrator, reviewer, publisher.
- **Histórias de usuário formais / catálogo UML de atores:** não identificado no texto da dissertação — registrar como lacuna; verificar se a implementação oferece evidência relacionada; não inventar personas.

## Solução proposta (terceiro ciclo)

Pipeline de MRV: upload/entrada → preservação do bruto (+ hash) → wrapper/extração → normalização → validação → representação semântica (AgroMRV-Lite, ontologia de trabalho) → cálculo preliminar → revisão humana → aprovação individual → aprovação geral → publicação na ontologia final / manifesto → pacote de evidências → hashes e raiz de Merkle (`json_canonical_v1`) → ancoragem (SimulatedAnchorProvider ou EvmAnchorProvider: Anvil / Ethereum Sepolia) via contrato `CarbonEvidenceRegistry` → consulta e verificação (correspondência/divergência, idempotência, adulteração controlada).

Frontend Dash atua como interface e orquestrador do fluxo, sem incorporar a lógica técnica interna dos serviços.

## Arquitetura esperada

- Separação de responsabilidades entre serviços (preservação, wrapper, validação, ontologia, cálculo, métricas, predição, proveniência, revisão/aprovação, publicação, evidências, blockchain, auditoria).
- Separação de estados: preliminar → em revisão → aprovado | rejeitado → publicado; correção/recálculo são eventos que geram nova versão preliminar.
- Separação cálculo × predição (estimativas preditivas só para consulta).
- Separação proveniência × blockchain (blockchain complementar após publicação).
- Porta `BlockchainAnchorProviderPort`; providers simulado e EVM.
- Gate: pacote final / ancoragem somente com publicação final.
- Idempotência: `SHA-256(network_code:package_hash)`; sem sobrescrita on-chain da mesma chave.
- Minimização on-chain: evidence key, package hash, Merkle root, responsável, momento.

## Tecnologias mencionadas

Python; Dash (UI/orquestração); wrappers de layouts; AgroMRV-Lite / OWL; proveniência inspirada em PROV-DM; SQLite (proveniência/evidências); filesystem; canonicalização `json_canonical_v1`; SHA-256; Merkle; Keccak-256 para `evidenceKey` EVM; Solidity (`CarbonEvidenceRegistry`: `anchorEvidence`, `getEvidence`, `evidenceExists`, `owner`, evento `EvidenceAnchored`); Anvil; Ethereum Sepolia; ABI versionada; aprendizado de máquina / modelos preditivos (dados aprovados e publicados).

## Interface esperada (seção 4.5.10)

Entrada de dados (propriedade, período, layout, arquivo); acompanhamento do ciclo com estados visuais; diferenciação de estados de resultado; indicadores/dashboard (CO2e, intensidade, evolução, fontes, produção, manejo, governança); análise de emissões; área separada de estimativas preditivas; revisão/aprovação/rejeição/correção com justificativa; publicação vinculada ao fluxo de aprovação (não tela independente de publicação final); auditoria técnica (proveniência, hashes, manifesto, pacote, Merkle, ancoragem simulada/EVM, verificação); metadados públicos EVM quando aplicável.

## Cenários de avaliação previstos (Capítulo 5)

O Capítulo 5 avalia a arquitetura em cenários representativos. No PDF analisado, o Cap. 5 ainda não estava redigido; a avaliação deve cobrir o previsto no Cap. 4:

- **CE1** — Preparação e representação dos dados.
- **CE2** — Cálculo e governança dos resultados.
- **CE3** — Predição e separação dos resultados.
- **CE4** — Proveniência, evidências e integridade (inclui EVM, idempotência, adulteração).
- **CE5** — Visualização e auditoria técnica.

## Resultados que devem ser demonstrados no Capítulo 5

Integração com diferentes granularidades; execução e revisão dos cálculos; separação dos estados; reconstrução da proveniência; geração de pacotes; ancoragem EVM; consulta on-chain; idempotência; verificação de integridade; operabilidade das interfaces; rastreabilidade requisito→componente→evidência (Tabelas 10 e 11 da dissertação).

## Limitações declaradas relevantes

Blockchain não valida qualidade do dado agropecuário; Sepolia é rede de testes; contrato tem escopo acadêmico; provider simulado permanece disponível; integridade criptográfica ≠ veracidade do dado.

## Nota sobre identificadores auxiliares

Os identificadores **RF00x** e **RNF00x** são oficiais da dissertação. Os identificadores **RN-xx** (regras de negócio derivadas das decisões arquiteturais), **RE-xx** (requisitos de avaliação/evidência) e a referência aos cenários **CE1–CE5** foram normalizados neste prompt **apenas para facilitar a rastreabilidade**; CE1–CE5 são oficiais da dissertação; RN/RE foram criados a partir do texto das decisões arquiteturais e do plano de avaliação do Cap. 5.

# ESCOPO DA AUDITORIA

Analisar todo o código autoral relevante do repositório, incluindo:

- frontend Dash (`frontend/`: `main.py`, páginas, rotas, layouts, componentes, callbacks, stores, CSS);
- view services e adapters (`frontend/services/`);
- orquestração (`local_orchestrator`, `cycle_state`, `pipeline_display`);
- módulos: save-file, wrappers, ontology-manager, calculation-service, model-training-service, traceability-service, blockchain-service;
- contratos Solidity, providers de ancoragem, canonicalização, pacotes de evidência;
- configuração, variáveis de ambiente **documentadas** (sem expor segredos);
- scripts de seed/smoke/validação;
- testes, mocks, documentação, build, lint, CI, Docker/infra local quando existirem;
- backend/DB/serviços apenas nos pontos necessários para validar requisitos e fluxos ponta a ponta.

Ignorar, salvo dependências necessárias à análise:

`node_modules`, venvs, dependências copiadas, artefatos gerados, builds, minificados, caches, binários, conteúdo não autoral.

**Atenção arquitetural da dissertação:** integração entre frontend e serviços é por chamada Python direta (adapters), não HTTP entre módulos no caminho Dash. Não confundir FastAPI opcional do traceability-service com o contrato do frontend. Não confundir hash de arquivo bruto ou registro de proveniência com ancoragem blockchain.

# RESTRIÇÕES DE SEGURANÇA E INTEGRIDADE

Trabalhe em modo de auditoria.

**Não** corrija código, refatore, altere dependências, apague arquivos, modifique configurações, execute migrações destrutivas, altere dados permanentes, faça commits, nem exponha segredos/tokens/senhas/chaves.

Pode criar **somente** arquivos de relatório em:

`docs/auditoria-capitulo-5/`

Se já existir `PROMPT-AUDITORIA-CURSOR.md` nesse diretório, não o sobrescreva com resultados; mantenha os relatórios nos nomes listados na seção ARQUIVOS DE SAÍDA.

Se identificar credenciais ou segredos, registre apenas a existência do problema, ocultando valores.

Scripts destrutivos (`reset_test_environment.py --confirm`, wipe de dados etc.) só com confirmação explícita do usuário; preferir análise estática e scripts de validação não destrutivos quando disponíveis.

# ETAPAS DA ANÁLISE

## Etapa 1 — Verificação inicial

1. Confirmar raiz do repositório.
2. Verificar estado da indexação do projeto.
3. Executar `git status` quando Git estiver disponível.
4. Identificar gerenciador de pacotes / venv / requirements.
5. Identificar scripts disponíveis (especialmente `frontend/scripts/`, docs de operações).
6. Ler documentação (`README.md`, `docs/`, READMEs dos serviços, ADRs).
7. Identificar a stack real.
8. Localizar entrypoints (`frontend/main.py`), rotas, páginas, componentes, serviços, testes, configurações.
9. Registrar arquivos/diretórios ignorados pela indexação que possam afetar a auditoria.

## Etapa 2 — Mapeamento do projeto

Criar mapa com: estrutura geral; módulos; responsabilidades; dependências internas; fluxo de navegação; fluxo de dados; comunicação frontend↔serviços; persistência; autenticação/autorização (se houver); tratamento de erros; estratégia de testes; ferramentas de build e qualidade.

Indicar caminhos exatos e nomes de símbolos. Se citar número de linha, citar também o nome do símbolo.

## Etapa 3 — Normalização dos requisitos

Partir da lista deste prompt. Para cada requisito: descrição original; tipo; ator; fluxo; critérios de aceitação; evidências esperadas; partes prováveis do projeto; dependências; ambiguidades.

Não substituir requisitos da dissertação por requisitos genéricos de mercado.

Quando informação não estiver na dissertação: registrar “não identificado no contexto da dissertação”; verificar se a implementação oferece evidência relacionada; concluir “não verificável” se não houver critério suficiente.

## Etapa 4 — Rastreabilidade requisito–implementação

Para cada requisito, rastrear quando aplicável:

`Requisito → rota/tela → componente → estado → serviço/adapter/API → regra de negócio → modelo de dados → teste → evidência visual`

Apontar: caminhos; símbolos; responsabilidades; trechos relevantes resumidos; testes; comandos; comportamento observado; lacunas.

Analisar dependências, imports, rotas e fluxos — não apenas busca textual.

## Etapa 5 — Execução e validação

Detectar comandos reais do projeto antes de executá-los. Quando disponíveis e seguros, executar: instalação/verificação de deps; lint/typecheck se oficiais; testes; build; inicialização da aplicação; scripts de validação documentados (smoke, pipeline, filtros, ciclo de emissão etc.).

Registrar: comando exato; finalidade; resultado; quantidade de testes; falhas; warnings relevantes; arquivos; impacto nos requisitos.

Não afirmar que um comando passou sem executá-lo. Se bloquear: o que tentou, motivo, erro, o que ainda vale por análise estática, o que ficou não verificável.

Existência de teste ≠ prova de requisito: verificar se executa, passa e cobre o comportamento.

## Etapa 6 — Avaliação requisito por requisito

Para cada RF, RNF, RN e RE, subseção com:

- identificador; descrição; classificação; confiança (alto/médio/baixo);
- implementação encontrada; arquivos e símbolos;
- comportamento esperado; comportamento observado;
- testes encontrados; testes executados; evidências;
- lacunas; impacto; recomendação de correção; evidência necessária para reclassificação.

### Regras de classificação

- **Atendido:** evidência suficiente de que todos os critérios essenciais estão implementados e funcionando.
- **Parcialmente atendido:** parte presente, mas critérios ausentes, incorretos, não testados ou incompletos.
- **Não atendido:** ausente, contradiz o requisito ou falha na validação.
- **Não aplicável:** justificativa clara de fora do escopo/versão avaliada.
- **Não verificável:** faltam informações, ambiente, dados, serviço externo, credenciais, critérios ou evidências.

# LISTA DE REQUISITOS A VERIFICAR

## Requisitos funcionais (oficiais da dissertação)

Para cada RF, use também o critério de atendimento e evidência esperada das Tabelas 10/11 da dissertação (reproduzidos abaixo). Critérios adicionais “inferidos” são marcados como tal.

### RF001 — Entrada de dados agropecuários

**Descrição:** A arquitetura deve permitir a entrada de dados agropecuários associados a uma propriedade, a um período de referência, a um ciclo de processamento e ao tipo de atividade representada (rebanho, produção, energia, fertilizantes, dejetos, dieta e demais variáveis necessárias aos cálculos).

**Grupo / QP / Cenário:** Entrada e preparação; QP1; CE1.

**Evidência esperada (dissertação):** Registro de entrada associado à propriedade, ao período, ao ciclo e ao tipo de atividade.

**Critério de atendimento (dissertação):** O dado recebido fica associado ao contexto mínimo exigido para iniciar a pipeline de MRV.

**Critérios verificáveis (inferidos):**

1. Ator: usuário responsável. Condição: sistema disponível. Ação: submeter arquivo/dados com propriedade, período, layout/ciclo. Esperado: ciclo criado/associado; observável na UI e/ou artefatos. Erro: feedback se contexto incompleto. Evidência: tela de entrada + artefato/registro.

### RF002 — Preservação dos dados brutos

**Descrição:** Preservar dados recebidos antes de qualquer transformação, com referência ao conteúdo original, metadados de entrada e identificador de integridade, permitindo recuperação e auditoria.

**QP/CE:** QP1; CE1. Componente: preservação dos dados brutos.

**Evidência esperada:** Artefato bruto, metadados e hash inicial.

**Critério:** Conteúdo originalmente recebido permanece recuperável após o processamento.

**Critérios verificáveis (inferidos):** Hash (ex.: SHA-256) gerado no ingresso; arquivo original persistido; recuperação posterior sem depender do normalizado.

### RF003 — Normalização e padronização dos dados

**Descrição:** Normalizar dados recebidos (estruturas, nomes, tipos, unidades, datas, granularidades) conforme contratos definidos.

**Evidência esperada:** Lote normalizado e registro das padronizações aplicadas.

**Critério:** Campos/tipos/unidades/datas/granularidades seguem contratos sem perda do vínculo com o dado bruto.

### RF004 — Validação da qualidade e da consistência

**Descrição:** Validar antes dos cálculos (completude, consistência, formato, domínio, unidade, período, compatibilidade com regras).

**Evidência esperada:** Resultado das validações e pendências identificadas.

**Critério:** Dados inconsistentes são identificados e não tratados como validados para etapas dependentes.

### RF005 — Associação às granularidades temporal e organizacional

**Descrição:** Associar dados às granularidades diária/mensal/anual e animal/lote/propriedade conforme origem e detalhamento.

**Evidência esperada:** Associações de granularidade temporal e organizacional.

**Critério:** Cada registro mantém granularidades compatíveis com origem e nível de detalhamento.

### RF006 — Registro de proveniência

**Descrição:** Registrar eventos de proveniência das etapas do ciclo de vida, incluindo entrada, preservação, extração, normalização, validação, integração semântica, cálculo, início da revisão, aprovação, rejeição, correção, recálculo, versionamento, publicação, geração de evidências, solicitação de ancoragem, confirmação da transação e verificação da evidência.

**QP/CE:** QP1 e QP3; CE1, CE2, CE4.

**Evidência esperada:** Entidades, atividades, agentes e relações registrados.

**Critério:** A trajetória entre dado bruto e resultado publicado pode ser reconstruída.

### RF007 — Representação semântica na ontologia de trabalho

**Descrição:** Representar semanticamente dados normalizados via ontologia do domínio. Dados, parâmetros e resultados preliminares em ontologia de trabalho enquanto o ciclo estiver em processamento, revisão ou aprovação.

**Evidência esperada:** Instâncias e relações na AgroMRV-Lite.

**Critério:** Dados normalizados/validados associados a conceitos canônicos e ao ciclo correspondente.

### RF008 — Cálculo preliminar de emissões

**Descrição:** Executar cálculos de GEE a partir de dados normalizados, validados e semanticamente organizados; resultados identificados como preliminares.

**Evidência esperada:** Execução de cálculo e resultado preliminar identificado.

**Critério:** Cálculo usa dados preparados; estado preliminar; sem publicação automática.

### RF009 — Registro dos parâmetros de cálculo

**Descrição:** Registrar, para cada cálculo, dados de entrada, parâmetros, fatores, unidades, métodos, fórmulas e versões.

**Evidência esperada:** Dados, fórmulas, métodos, versões, fatores, parâmetros e unidades registrados.

**Critério:** Condições do cálculo recuperáveis a partir do resultado.

### RF010 — Correção e atualização dos resultados preliminares

**Descrição:** Permitir correção de dados/parâmetros/fatores; registrar evento; recálculo produz nova versão preliminar; proveniência mantém histórico.

**Evidência esperada:** Resultado anterior, correção, evento de recálculo e nova versão preliminar.

**Critério:** Correção e recálculo produzem nova versão e preservam histórico.

### RF011 — Predição de emissões e produção

**Descrição:** Treinamento, avaliação, seleção e versionamento de modelos; usar dados aprovados e publicados quando houver quantidade/qualidade suficientes; estimativas só para consulta, sem publicação como resultados calculados/observados na ontologia final.

**CE:** CE3.

**Evidência esperada:** Versão do modelo, métricas de avaliação e estimativa consultável.

**Critério:** Estimativa usa dados aprovados/publicados e não é publicada como resultado calculado/observado.

### RF012 — Cálculo de métricas e indicadores

**Descrição:** Calcular e disponibilizar métricas derivadas (evolução temporal, produção, intensidade, eficiência produtiva, sustentabilidade, manejo).

**Evidência esperada:** Métricas/indicadores associados aos resultados de origem.

**Critério:** Indicadores como artefatos derivados, distintos dos resultados primários.

### RF013 — Revisão humana

**Descrição:** Usuário responsável examina dados, parâmetros e resultados preliminares antes da publicação; ao iniciar análise, estado passa de preliminar para em revisão.

**Evidência esperada:** Registro de revisão com resultado, agente, momento e transição de estado.

**Critério:** Início da análise altera preliminar → em revisão e mantém ação humana registrada.

### RF014 — Aprovação ou rejeição individual dos cálculos

**Descrição:** Aprovar, rejeitar ou solicitar correção de cada cálculo em revisão; estados aprovado/rejeitado; correção + recálculo → nova versão preliminar; rejeições e solicitações de correção com justificativa.

**Evidência esperada:** Decisão individual, transição e evento de correção quando aplicável.

**Critério:** Decisão altera estado; correção+recálculo gera nova versão preliminar.

### RF015 — Aprovação geral do ciclo

**Descrição:** Aprovação geral somente após todos os cálculos obrigatórios avaliados individualmente e no estado aprovado.

**Evidência esperada:** Tentativas de aprovação geral antes e depois da aprovação individual.

**Critério:** Aprovação geral bloqueada enquanto algum resultado obrigatório não estiver aprovado.

### RF016 — Publicação na ontologia final

**Descrição:** Publicar na ontologia final somente resultados aprovados individualmente e associados a ciclo com aprovação geral concluída. Preliminares, em revisão ou rejeitados não devem ser publicados.

**Evidência esperada:** Comparação entre ontologia de trabalho e ontologia final.

**Critério:** Somente resultados aprovados e associados a ciclo aprovado são publicados.

### RF017 — Geração de evidências técnicas

**Descrição:** Gerar pacote de evidências associado aos resultados publicados, relacionando publicação a dados, cálculos, parâmetros, aprovações, proveniência e demais artefatos relevantes.

**CE:** CE4.

**Evidência esperada:** Pacote de evidências e manifesto de publicação.

**Critério:** Pacote relaciona publicação aos elementos previstos.

### RF018 — Geração e verificação de identificadores criptográficos

**Descrição:** Gerar hashes de dados brutos, resultados publicados, evidências e artefatos relevantes; pacote com canonicalização versionada, hash do pacote e raiz de Merkle; permitir comparação com valores recalculados localmente e, quando aplicável, da blockchain.

**Evidência esperada:** Hash do pacote e raiz de Merkle registrados e recalculados.

**Critério:** Alterações produzem divergência; pacote original mantém correspondência local e, quando aplicável, on-chain.

### RF019 — Ancoragem de evidências em blockchain

**Descrição:** Ancorar somente após aprovação geral e publicação na ontologia final; registrar identificador da evidência, hash do pacote e raiz de Merkle; persistir metadados da transação; impedir envio duplicado da mesma evidência para a mesma rede.

**Evidência esperada:** Rede, contrato, hash da transação, bloco, recibo, evento e vínculo com o pacote.

**Critério:** Ancoragem só após publicação final; registra identificadores; sem nova transação para solicitação idempotente.

### RF020 — Visualização e auditoria técnica

**Descrição:** Interfaces para entrada, indicadores, análise de emissões, revisão/aprovação, predição, acompanhamento do ciclo e auditoria técnica. Com ancoragem EVM: metadados públicos da transação e estado da verificação.

**CE:** CE2, CE4, CE5.

**Evidência esperada:** Telas e consultas para acompanhamento, revisão, predição, evidências, ancoragem e auditoria.

**Critério:** Funções acessíveis sem depender exclusivamente de código-fonte ou consultas manuais ao banco.

### RF021 — Consulta e verificação da evidência ancorada

**Descrição:** Consultar evidência na blockchain, recuperar identificadores do contrato e compará-los com valores recalculados do pacote local; indicar correspondência ou divergência sem alterar o registro na rede.

**Evidência esperada:** Consulta ao contrato e valores recuperados (hash do pacote e Merkle).

**Critério:** Valores on-chain correspondem aos recalculados do pacote local; cópia adulterada produz divergência.

---

## Requisitos não funcionais (oficiais)

### RNF001 — Rastreabilidade

**Propriedade:** A partir de resultado publicado, recuperar artefato bruto, lote extraído, normalizado, validado, representação semântica, execução de cálculo, parâmetros/fatores, decisões de revisão/aprovação, publicação, evidências e, quando aplicável, ancoragem.

**Critério observável:** Trajetória reconstruível via proveniência e vinculada ao pacote/transação.

### RNF002 — Auditabilidade

**Propriedade:** Eventos, artefatos, agentes, estados e momentos consultáveis pela interface de auditoria técnica; com EVM: rede, contrato, transação, recibo e resultado da verificação consultáveis.

**Critério:** Consultas pelas interfaces, sem depender exclusivamente de código-fonte ou acesso manual ao DB.

### RNF003 — Manutenibilidade

**Propriedade:** Alterações em layouts, cálculos, fatores, parâmetros, regras de validação ou modelos preditivos concentradas nos componentes responsáveis.

**Critério:** Em cenário de alteração selecionada, modificar sem reescrever componentes não relacionados. (Não pressupõe manutenibilidade plena a priori.)

### RNF004 — Integridade

**Propriedade:** Comparar hashes e Merkle recalculados com pacote e, quando aplicável, blockchain.

**Critério:** Original corresponde; cópia adulterada diverge; revalidação do original mantém correspondência. Integridade criptográfica ≠ veracidade do dado agropecuário.

### RNF005 — Explicabilidade

**Propriedade:** Para cada resultado calculado, identificar dados, fórmula, método, versão, fatores, parâmetros, unidades, GWP, período, granularidade e responsável pela execução ou aprovação.

**Critério:** Recuperação dessas informações a partir do resultado selecionado.

### RNF006 — Consistência semântica

**Propriedade:** Vocabulário canônico para propriedades, ciclos, períodos, granularidades, fontes, gases, variáveis, cálculos, resultados, estimativas preditivas, publicações e evidências.

**Critério:** Fontes distintas mapeadas aos mesmos conceitos; inconsistências semânticas previstas detectadas antes de etapas dependentes.

### RNF007 — Operabilidade das interfaces

**Propriedade:** Funções de acompanhamento, revisão, consulta, auditoria e verificação acessíveis pelas interfaces do protótipo.

**Critério:** Usuário responsável executa tarefas previstas pelas interfaces; **não** é avaliação de usabilidade com usuários.

### RNF008 — Extensibilidade

**Propriedade:** Inclusão de novo layout, fonte de emissão, cálculo, regra, métrica, modelo preditivo ou provider de blockchain pelos pontos de extensão.

**Critério:** Extensão altera apenas componentes relacionados; provider EVM não modifica regras de pacote, canonicalização, integridade ou publicação final.

### RNF009 — Reprodutibilidade

**Propriedade:** Mesma execução (dados, parâmetros, fatores, métodos, versões, período, granularidade) → mesmo resultado (tolerância numérica); evidências com `json_canonical_v1` → mesmo hash e mesma Merkle.

**Critério:** Duas execuções equivalentes correspondentes; mesmas condições de canonicalização produzem mesmos identificadores.

### RNF010 — Versionamento

**Propriedade:** Cada ciclo identifica versões de layouts, modelos semânticos, fórmulas, métodos, fatores, parâmetros, modelos preditivos, estruturas de publicação, estratégias de canonicalização e interfaces do contrato inteligente.

**Critério:** Versões recuperáveis a partir do ciclo, resultado ou pacote.

### RNF011 — Interoperabilidade

**Propriedade:** Troca por contratos/formatos estruturados com identificadores de encadeamento; blockchain com ABI versionada, tipos EVM e estruturas de comandos/resultados/recibos/eventos.

**Critério:** Artefatos consumíveis pela etapa seguinte; exportações nos formatos definidos; serviço Python envia/consulta/interpreta contrato Solidity conforme ABI.

### RNF012 — Proteção de credenciais e minimização on-chain

**Propriedade:** Chaves privadas, tokens RPC, dados brutos e conteúdos completos dos pacotes não persistidos em código-fonte, logs, banco de evidências ou blockchain. On-chain só identificadores necessários.

**Critério:** Credenciais por configuração externa; logs/relatórios sem segredos; contrato registra apenas chave da evidência, hash do pacote, Merkle, responsável e momento.

---

## Regras de negócio / decisões arquiteturais (IDs auxiliares RN-*)

Derivadas da seção “Decisões arquiteturais” da dissertação (não eram RN numerados no original).

### RN-01 — Separação de responsabilidades entre serviços

Frontend pode orquestrar e apresentar estados, sem incorporar lógica técnica interna dos serviços.

### RN-02 — Separação entre estados dos resultados

Estados: preliminar, em revisão, aprovado, rejeitado, publicado. Correção/recálculo não são estados persistentes; são eventos que geram nova versão preliminar.

### RN-03 — Separação entre cálculo e predição

Estimativas preditivas não podem ser publicadas na ontologia final como resultados calculados ou observados.

### RN-04 — Separação entre proveniência e blockchain

Blockchain não substitui proveniência, bancos operacionais nem auditoria técnica; só ancoragem/consulta após publicação.

### RN-05 — Abstração dos providers de ancoragem

Dependência de `BlockchainAnchorProviderPort`; `SimulatedAnchorProvider` e `EvmAnchorProvider` sem duplicar regras de geração/consulta/verificação.

### RN-06 — Canonicalização única dos pacotes

Estratégia versionada `json_canonical_v1` (UTF-8, ordenação determinística) compartilhada por evidências, blockchain, frontend e verificação.

### RN-07 — Gate de publicação final

Construção do pacote final, solicitação de ancoragem e envio da transação somente com publicação final registrada. Impede uso de preliminares/em revisão/rejeitados/apenas aprovados individualmente como evidência final.

### RN-08 — Idempotência e proibição de sobrescrita

Chave `SHA-256(network_code:package_hash)` com unicidade; contrato não sobrescreve evidence key já registrada.

### RN-09 — Minimização dos registros on-chain

On-chain: chave, package hash, Merkle, endereço responsável, momento. Escrita restrita à carteira proprietária; consultas públicas. Credenciais fora do código-fonte.

### RN-10 — Publicação vinculada à aprovação

Publicação acionada a partir do fluxo de aprovação, não por tela independente de publicação final (seção 4.5.10).

---

## Requisitos de avaliação / evidência (IDs auxiliares RE-*)

Alinhados aos cenários CE e ao Cap. 5 previsto.

### RE-01 / CE1 — Preparação e representação

Demonstrar entrada, preservação, extração, normalização, validação, granularidades e representação semântica com evidências reproduzíveis.

### RE-02 / CE2 — Cálculo e governança

Demonstrar cálculo preliminar, parâmetros, correção/recálculo, revisão, aprovação individual/geral e publicação.

### RE-03 / CE3 — Predição e separação

Demonstrar treinamento/consulta de modelos e separação visual/semântica entre estimativa preditiva e resultado calculado.

### RE-04 / CE4 — Proveniência, evidências e integridade

Demonstrar linhagem, pacote, canonicalização, hashes, Merkle, ancoragem EVM (ou simulado documentado), consulta on-chain, idempotência e adulteração controlada.

### RE-05 / CE5 — Visualização e auditoria técnica

Demonstrar que as funções previstas são executáveis pelas interfaces (operabilidade), incluindo auditoria e verificação.

### RE-06 — Matriz Cap. 5

Consolidar status de RF001–RF021 e RNF001–RNF012 com evidências para redação do Capítulo 5, sem antecipar atendimento sem prova.

---

## Lacunas explícitas da dissertação (tratar como não inventar)

- Resumo/abstract e palavras-chave incompletos no PDF de origem.
- Capítulos 3 e 5 sem texto completo no sumário do PDF analisado (Cap. 5 previsto, não redigido).
- Catálogo formal de histórias de usuário / casos de uso UML: não identificado.
- Autenticação/autorização multi-perfil detalhada: não identificada como requisito formal (há “usuário responsável”).
- Critérios de acessibilidade WCAG, i18n, responsividade mobile: não identificados como requisitos acadêmicos oficiais — avaliar só na seção complementar, sem alterar status dos RF/RNF salvo se o requisito exigir.

# VERIFICAÇÕES TÉCNICAS COMPLEMENTARES

Seção separada; **não** altera classificação dos requisitos acadêmicos, salvo quando o próprio requisito exigir a característica.

Analisar quando aplicável: organização arquitetural; SoC; duplicação; acoplamento; coesão; consistência de componentes; tipos; estados loading/vazio/sucesso/erro; validação de entrada; feedback; responsividade; semântica HTML; teclado/foco/rótulos/alt/contraste; WCAG 2.2 quando verificável; exposição de dados; armazenamento inseguro; injeção/XSS; controle de acesso; tokens; OWASP ASVS relevante; desempenho; bundle; falhas de rede; observabilidade; testabilidade; manutenibilidade; documentação.

Classificar achados como: (1) requisito da dissertação; (2) defeito que impede requisito; (3) dívida técnica; (4) melhoria opcional; (5) risco não confirmado.

# MATRIZ DE RASTREABILIDADE

Produzir tabela com colunas mínimas:

| ID | Requisito | Critérios de aceitação | Tela/fluxo | Arquivos e símbolos | API/dados | Testes | Evidências | Status | Confiança | Lacunas |

Múltiplos critérios: lista numerada na célula ou linhas separadas.

Não calcular índices ponderados ou notas arbitrárias.

Opcionalmente informar apenas contagens e percentuais simples por classificação.

# PLANO DE EVIDÊNCIAS PARA O CAPÍTULO 5

Lista de evidências visuais e técnicas utilizáveis na dissertação.

Para cada screenshot:

- identificador; requisito comprovado; rota/tela; perfil; pré-condições; dados necessários; ações; estado exato da UI; elemento principal; elementos a destacar; o que comprova; o que não comprova; legenda acadêmica sugerida; nome de arquivo; necessidade de ocultar PII.

Nomes: `EVID-RF001-01-descricao-curta.png`

Fluxos multi-imagem: (1) estado inicial; (2) ação; (3) resultado; (4) confirmação/persistência.

Não usar screenshot de código como única prova de comportamento demonstrável na UI. Não usar screenshot de UI como prova isolada de regra interna, persistência ou segurança.

Evidências não visuais sugeridas: saída de teste/build/cobertura; log sanitizado; resposta/consulta sanitizada; diagrama; matriz; trecho pequeno de código relevante.

Priorizar telas/fluxos alinhados à dissertação e ao protótipo: Painel/Indicadores; Entrada de Dados; Cálculos; Revisão e Aprovação; Predição; Auditoria Técnica / Proveniência; Blockchain e Evidências; Verificação de Integridade; stepper de pipeline com gate pós-publicação.

# MATERIAL PARA REDAÇÃO DO CAPÍTULO 5

Seção `Texto-base para o Capítulo 5` em português brasileiro, linguagem técnica e impessoal, baseada exclusivamente nas evidências encontradas.

Organização:

1. procedimento de avaliação;
2. ambiente avaliado;
3. mapeamento da implementação;
4. atendimento aos requisitos funcionais;
5. atendimento aos requisitos não funcionais;
6. resultados dos testes;
7. evidências da interface;
8. limitações da avaliação;
9. requisitos parcialmente ou não atendidos;
10. síntese dos resultados.

Regras do texto: sem tom publicitário; sem afirmações sem evidência; referenciar IDs de requisitos e evidências; diferenciar análise estática de teste executado; não inventar números; usar marcações `[INSERIR FIGURA EVID-RF001-01]`; sugerir legendas; apresentar como texto-base sujeito à revisão do pesquisador.

# ARQUIVOS DE SAÍDA

Criar:

1. `docs/auditoria-capitulo-5/relatorio-completo.md`
2. `docs/auditoria-capitulo-5/matriz-rastreabilidade.md`
3. `docs/auditoria-capitulo-5/plano-evidencias.md`
4. `docs/auditoria-capitulo-5/texto-base-capitulo-5.md`
5. `docs/auditoria-capitulo-5/comandos-e-resultados.md`
6. `docs/auditoria-capitulo-5/pendencias.md`

Se não houver permissão para criar arquivos, apresentar todo o conteúdo na conversa com a mesma estrutura.

# ESTRUTURA DO RELATÓRIO FINAL

O `relatorio-completo.md` deve conter:

1. identificação da versão analisada;
2. data e ambiente da auditoria;
3. escopo;
4. limitações;
5. metodologia de análise;
6. mapa do repositório;
7. arquitetura observada;
8. lista normalizada de requisitos;
9. matriz de rastreabilidade;
10. análise detalhada por requisito;
11. comandos executados;
12. resultados dos testes;
13. análise técnica complementar;
14. plano de screenshots;
15. riscos e lacunas;
16. recomendações priorizadas;
17. texto-base para o Capítulo 5;
18. checklist de revisão manual.

# PRIORIZAÇÃO DOS PROBLEMAS

Classificar pendências: crítica; alta; média; baixa; informativa.

Considerar: requisito acadêmico afetado; impacto no usuário; risco de funcionamento incorreto; risco para dados; dificuldade de demonstração no Cap. 5; risco às conclusões da dissertação.

Para cada pendência: problema; requisito afetado; evidência; impacto; correção recomendada; arquivos provavelmente envolvidos; forma de validar a correção.

# CHECKLIST FINAL DO CURSOR

Antes de concluir, conferir:

- todos os requisitos (RF, RNF, RN, RE) foram avaliados;
- todos os status possuem justificativa;
- todas as conclusões possuem evidência;
- caminhos de arquivos são reais;
- símbolos citados existem;
- comandos apresentados foram realmente executados;
- falhas não foram ocultadas;
- não houve confusão entre frontend e serviços / proveniência e blockchain / cálculo e predição;
- requisitos acadêmicos separados das recomendações complementares;
- screenshots possuem roteiro reproduzível;
- texto do Cap. 5 sem afirmações inventadas;
- segredos e dados pessoais ocultados;
- nenhum código da aplicação foi modificado (exceto criação dos relatórios em `docs/auditoria-capitulo-5/`).

# INÍCIO

Execute as Etapas 1–6 agora, no repositório atual, e produza os arquivos de saída listados.
