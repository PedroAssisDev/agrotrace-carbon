# Modelo de Payload de Ancoragem

## 1) Objetivo do payload

O payload de ancoragem define uma estrutura JSON padrao para representar evidencias de integridade de resultados de carbono. Nesta fase, ele existe para:

- padronizar os dados minimos que poderao ser ancorados no futuro;
- preservar rastreabilidade e auditoria;
- permitir validacao estrutural com JSON Schema;
- evitar acoplamento prematuro com qualquer tecnologia de rede.

## 2) Por que o modelo e generico

O modelo foi desenhado para ser agnostico de rede e provider. Isso significa que o dominio (intencao de ancoragem, pacote de evidencia e provas de integridade) nao depende de detalhes de implementacao de uma blockchain especifica.

Com esse desenho, o mesmo payload pode ser convertido no futuro para diferentes mecanismos de submissao, sem alterar o contrato de dados do dominio.

## 3) Por que ainda nao escolhemos rede blockchain

A escolha da rede depende de fatores nao funcionais (custo, throughput, privacidade, compliance, governanca e operacao). Antecipar essa decisao agora geraria acoplamento tecnico sem necessidade.

Nesta fase, o foco e validar a qualidade do modelo de dados que sera ancorado, independentemente da rede.

## 4) Por que nao enviamos dados sensiveis completos para blockchain

Dados completos podem conter informacoes sensiveis ou reguladas. Publicar esse conteudo em camada imutavel e potencialmente publica aumenta riscos de privacidade, exposicao comercial e compliance.

Por isso, este modelo prioriza:

- hashes de evidencias;
- identificadores minimos;
- metadados essenciais;
- resumo publico opcional.

## 5) Por que usamos hashes

Hash criptografico permite comprovar integridade sem expor o conteudo original. Se o dado original mudar, o hash muda. Assim, o processo de auditoria pode validar consistencia entre o artefato interno e o registro ancorado.

No MVP, os algoritmos permitidos sao `sha256` (padrao) e `sha3_256`.

## 6) O que e `package_hash`

`package_hash` representa a impressao criptografica do pacote logico de evidencias que suporta um resultado. Ele e a prova principal de integridade do pacote naquela versao.

Em termos praticos, e o hash que comprova que o conjunto validado internamente e o mesmo conjunto referenciado no payload de ancoragem.

## 7) O que e `merkle_root`

`merkle_root` e um resumo criptografico opcional de um conjunto de itens (tipicamente organizado em arvore de Merkle). Ele permite provar inclusao de itens individuais sem publicar todos os dados.

Neste modelo, ele e opcional para manter simplicidade no MVP, mas ja previsto para evolucao.

## 8) O que e `metadata_hash`

`metadata_hash` representa a integridade de metadados associados ao pacote (por exemplo, contexto tecnico, versoes, referencias internas minimas). Assim como `package_hash`, serve para verificacao posterior de consistencia.

## 9) O que e `public_summary`

`public_summary` controla a publicacao opcional de um resumo de emissao:

- `enabled = false`: nao publica total de emissao; campos de resumo ficam nulos.
- `enabled = true`: publica resumo minimo (tipo de resultado, valor escalado, unidade e escala).

## 10) Quando publicar ou nao publicar a emissao total

Publicar a emissao total pode ser util para transparencia externa. Nao publicar pode ser preferivel quando houver sensibilidade comercial, obrigacoes contratuais ou estrategia de divulgacao em fases.

O modelo suporta ambas as politicas sem mudar o restante do payload.

## 11) Diferenca entre payload privado e payload com resumo publico

- **Payload privado**: prioriza apenas provas de integridade (`package_hash`, `metadata_hash`, opcionalmente `merkle_root`) e metadados minimos.
- **Payload com resumo publico**: mantem as mesmas provas de integridade e adiciona resumo agregado de emissao, sem expor dados detalhados de calculo.

## 12) Evolucao futura para qualquer rede/provider

A secao `anchoring` existe para capturar estado de ancoragem sem fixar tecnologia. No MVP, ela aceita o modo `not_selected_yet` e status iniciais sem exigir rede, contrato ou transacao real.

No futuro, um adapter/provider podera mapear esse payload para:

- redes publicas permissionless;
- redes permissionadas;
- simulacao local de ancoragem.

Esse desenho preserva Clean Architecture: o dominio de dados permanece estavel e a infraestrutura de blockchain entra como detalhe substituivel.
