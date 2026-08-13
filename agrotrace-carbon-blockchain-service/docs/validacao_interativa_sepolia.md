# Validação interativa Ethereum Sepolia

## Objetivo

O script `validar_sepolia_interativo.py` (raiz do módulo) executa uma validação **interativa** e **segura** da integração real com a Ethereum Sepolia: configuração, RPC, carteira, contrato, pacote elegível, gate de publicação final, ancoragem real (mediante ENTER), consulta, verificação, idempotência e adulteração controlada em memória.

## Pré-requisitos

- Python 3.11+
- Ambiente virtual com dependências do módulo (`python -m pip install -e ".[dev]"`)
- Arquivo `.env` preenchido (RPC, chave, contrato, chain ID `11155111`)
- Contrato `CarbonEvidenceRegistry` implantado na Sepolia
- Carteira owner com SepoliaETH
- Ao menos um pacote de evidência elegível (`FINAL_ONTOLOGY_PUBLISHED` ou alias)

## Comandos

Na raiz de `agrotrace-carbon-blockchain-service`:

```powershell
python validar_sepolia_interativo.py
```

Com pacote específico:

```powershell
python validar_sepolia_interativo.py --package-id <UUID>
```

Somente consulta (não envia transação):

```powershell
python validar_sepolia_interativo.py --package-id <UUID> --query-only
```

Retomada de recibo (não reenvia):

```powershell
python validar_sepolia_interativo.py `
  --package-id <UUID> `
  --resume-transaction <TRANSACTION_HASH>
```

## Fluxo dos testes

1. Raiz do módulo
2. Arquivo `.env`
3. Variáveis obrigatórias
4. RPC Sepolia
5. Carteira e saldo
6. Bytecode do contrato
7. ABI
8. Owner / autorização
9. `ServiceContainer` e banco
10. Seleção do pacote
11. Gate de publicação final
12. Verificação off-chain
13. Cálculos derivados (`evidence_key`, `idempotency_key`)
14. Consulta on-chain prévia
15. Ancoragem real ou reaproveitamento idempotente
16. Recibo independente
17. Evento `EvidenceAnchored`
18. Consulta pós-ancoragem (UC + Web3.py)
19. Verificação completa
20. Idempotência
21. Adulteração em memória
22. Revalidação do original

Antes de cada teste o script descreve objetivo/ação/resultado e aguarda ENTER. Depois de cada teste, aguarda ENTER novamente. Qualquer texto diferente de ENTER encerra a execução.

## Testes que enviam transação

Somente o **Teste 15** pode enviar uma transação real (e consumir SepoliaETH), e apenas após confirmação explícita por ENTER em branco.

O **Teste 20** (idempotência) chama novamente o caso de uso oficial, mas **não** deve gerar nova transação.

Modos `--query-only` e `--resume-transaction` não enviam nova ancoragem.

## Como escolher o package ID

- Com `--package-id`: usa o UUID informado (após validar existência e gate).
- Sem argumento: lista até 20 candidatos elegíveis.
- Se a lista estiver vazia (ou se você pressionar ENTER na escolha): o script **oferece criar um pacote de exemplo** no SQLite local, com `FINAL_ONTOLOGY_PUBLISHED` e hashes oficiais. Isso **não** envia transação Sepolia.
- Confirmação: ENTER vazio cria; qualquer texto cancela.
- Flag opcional: `--create-sample-package` (ainda pede ENTER antes de gravar).
- O script **não** escolhe um pacote silenciosamente.

## Interpretação dos status

| Status | Significado |
|---|---|
| `PASSOU` | Critérios do teste atendidos |
| `FALHOU` | Critério obrigatório não atendido (pode interromper) |
| `AVISO` | Situação arriscada (ex.: saldo zero) |
| `IGNORADO` | Teste não aplicável (ex.: `--query-only`) |

## Arquivos gerados

Em `evidence/sepolia/interactive_validation_<YYYYMMDD_HHMMSS>/`:

- `environment_validation.json`, `rpc_validation.json`, `wallet_validation.json`
- `contract_validation.json`, `package_validation.json`
- `pre_anchor_query.json`, `anchoring_result.json`, `transaction_receipt.json`
- `contract_event.json`, `post_anchor_query.json`, `integrity_verification.json`
- `idempotency_validation.json`, `tampering_validation.json`, `original_revalidation.json`
- `public_links.json`, `summary.json`, `execution.log`
- Em sucesso completo: `VALIDACAO_EXECUTADA.md`

Nenhum JSON contém chave privada, RPC com token ou conteúdo do `.env`.

## Proteção de segredos

- RPC sanitizado (`…/v2/********`)
- Chave privada nunca impressa
- Logger com redação
- Evidências passam por `sanitize_mapping`

## Consulta no explorador

Após ancoragem:

```text
https://sepolia.etherscan.io/tx/<transaction_hash>
https://sepolia.etherscan.io/address/<contract_address>
```

Links também ficam em `public_links.json`.

## Executar novamente sem nova transação

Repetir a ancoragem do mesmo pacote na mesma rede deve retornar `idempotent_reuse = true` (mesmo `transaction_hash` e `block_number`). Use o Teste 20 do script ou:

```powershell
python -m app.interfaces.cli anchor-package `
  --package-id <UUID> `
  --network-code ethereum_sepolia
```

## Manual completo

Ver guia operacional [sepolia_deployment.md](sepolia_deployment.md) e o guia longo arquivado em
[`../../docs/archive/GUIA_COMPLETO_ETHEREUM_SEPOLIA.md`](../../docs/archive/GUIA_COMPLETO_ETHEREUM_SEPOLIA.md).
