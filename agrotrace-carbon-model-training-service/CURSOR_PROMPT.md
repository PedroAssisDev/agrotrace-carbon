# Prompt inicial para usar no Cursor

Analise todo este projeto antes de alterar qualquer arquivo. Leia primeiro:

1. `PROJECT_SPEC.md`;
2. `.cursor/rules/model-training-service.mdc`;
3. `README.md`;
4. os testes em `tests/`.

O projeto é um módulo acadêmico focado exclusivamente na geração de modelos. Não implemente frontend nem inferência nesta etapa.

Regras que não podem ser alteradas:

- regressão com apenas `lactating_cows` como feature;
- modelos separados para produção total de leite e emissão total;
- regressão mensal e anual com horizonte semântico de um próximo período;
- séries temporais apenas mensais, univariadas e específicas por propriedade;
- séries temporais sem variáveis exógenas;
- horizonte temporal registrado de três meses;
- treinamento somente com resultados aprovados e publicados;
- salvamento de modelo, métricas, metadados, versão, hash e dados usados;
- validação temporal sem embaralhamento para séries temporais.

Comece executando `pytest`. Depois, avalie a estrutura e produza um relatório com:

- o que já está implementado;
- o que falta para conectar a consulta SPARQL à ontologia real do agromrv-lite;
- possíveis inconsistências com a especificação;
- melhorias necessárias sem ampliar o escopo.

Não faça alterações até terminar essa análise inicial.
