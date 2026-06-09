# agrotrace-carbon-blockchain-service

## Fase atual: modelagem generica do payload de ancoragem

Esta fase estabelece apenas a base de dados para ancoragem futura, com foco em integridade, rastreabilidade e validacao estrutural de payloads JSON.

Limites desta fase:

- ainda nao ha integracao com servico de proveniencia;
- ainda nao ha blockchain real;
- ainda nao ha provider;
- ainda nao ha smart contract;
- o objetivo agora e validar a estrutura dos dados que futuramente serao ancorados;
- o payload foi desenhado para aceitar hash/Merkle Root obrigatorios e emissao total opcional.

## Estrutura desta etapa

- `schemas/anchor_payload.schema.json`: schema JSON do payload de ancoragem.
- `data/examples/anchor_payload_private.example.json`: exemplo sem publicacao de emissao total.
- `data/examples/anchor_payload_public_summary.example.json`: exemplo com resumo publico habilitado.
- `data/examples/*.jsonc`: versoes comentadas dos exemplos para leitura humana.
- `docs/anchor_payload_model.md`: explicacao tecnica e didatica do modelo.
- `tests/test_anchor_payload_schema.py`: testes de validacao dos exemplos e cenarios invalidos.

## Como rodar os testes

1. Instale a dependencia:
   - `pip install jsonschema`
2. Execute:
   - `python -m unittest tests/test_anchor_payload_schema.py`
