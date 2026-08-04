# Guia completo — Ethereum Sepolia no AgroTrace Carbon Blockchain Service

Manual autossuficiente para reproduzir, desde a criação da carteira até a ancoragem e consulta final, a validação real na testnet Ethereum Sepolia.

**Aviso de segurança:** este documento usa apenas *placeholders*. Nunca publique chave privada, frase de recuperação, API key Alchemy, token de RPC ou URL RPC autenticada completa.

---

## 1. Objetivo da validação

Demonstrar, de forma auditável, que o módulo:

1. preserva evidências off-chain (hashes, Merkle Root, pacote canônico);
2. só ancora após publicação final (`FINAL_ONTOLOGY_PUBLISHED` e aliases);
3. envia uma transação **real** para a Sepolia quando necessário;
4. consulta o contrato on-chain;
5. verifica coincidência de `packageHash` e `merkleRoot`;
6. respeita idempotência (não reenvia a mesma evidência);
7. detecta adulteração de payload em memória;
8. gera evidências públicas (JSON) sem segredos.

O script interativo oficial é:

```text
validar_sepolia_interativo.py
```

Documentação curta: [docs/validacao_interativa_sepolia.md](docs/validacao_interativa_sepolia.md).

---

## 2. Visão geral da Ethereum Sepolia

Sepolia é uma **testnet** pública da Ethereum. Serve para ensaios sem valor financeiro real.

| Conceito | Significado |
|---|---|
| Rede principal (mainnet) | ETH real; nunca use nesta dissertação/protótipo |
| Sepolia | Testnet; SepoliaETH sem valor comercial |
| Anvil | EVM local (Foundry); não é rede pública |
| `local_simulated` | Provider simulado do módulo; sem blockchain real |

Chain ID oficial da Sepolia: **11155111**.

Network code no módulo: **`ethereum_sepolia`**.

---

## 3. Diferença entre mainnet, testnet, Anvil e simulação

- **Mainnet:** ativos reais; proibida para este protótipo.
- **Sepolia:** rede pública de teste; transações visíveis no Etherscan Sepolia.
- **Anvil:** nó local (`http://127.0.0.1:8545`), chain ID `31337`; ideal para CI.
- **`local_simulated`:** não abre Web3; gera hashes de transação fictícios.

A validação interativa deste guia exige **Sepolia real**. Não use fallback silencioso para Anvil ou simulação.

---

## 4. Criação da carteira MetaMask

### Instalação

1. Instale a extensão **somente** pela fonte oficial da MetaMask (site metamask.io / loja oficial do navegador).
2. Evite extensões de terceiros com nome parecido.
3. Abra a extensão e selecione **Criar uma nova carteira**.
4. Defina uma senha local do aplicativo.
5. Anote a **Frase de Recuperação Secreta** (12/24 palavras) em papel, offline.
6. Nunca fotografe, não envie por chat, e-mail ou repositório.
7. Confirme a frase conforme solicitado pela MetaMask.

### Conta exclusiva da dissertação

1. Crie uma conta adicional, por exemplo: `AgroTrace Sepolia`.
2. Não misture com carteiras que já tenham ativos principais.
3. Use esta conta apenas para testnet.

### Ativar Sepolia

1. Abra o seletor de redes.
2. Ative **Mostrar redes de teste** / *Show test networks*.
3. Selecione **Sepolia**.
4. Confirme que o saldo exibido é SepoliaETH (não ETH mainnet).

### Endereço público

1. Copie o endereço da conta `AgroTrace Sepolia`.
2. Ele começa com `0x` e tem 42 caracteres.
3. Ao colar em qualquer formulário, confira os **primeiros e últimos** caracteres.

```text
Endereço público:
- pode ser compartilhado;
- começa com 0x;
- recebe SepoliaETH;
- aparece no explorador.

Chave privada:
- nunca deve ser compartilhada;
- assina transações;
- fica apenas no .env local;
- quem possui essa chave controla a carteira.

Frase de recuperação:
- recupera toda a carteira;
- nunca deve aparecer no código;
- nunca deve ser enviada;
- deve ser guardada offline.
```

---

## 5. Exportação da chave privada para o módulo

Interface típica da MetaMask (nomes podem variar levemente entre versões):

1. Abrir o seletor de contas.
2. Localizar `AgroTrace Sepolia`.
3. Abrir detalhes da conta.
4. Acessar a opção de chaves privadas / *Account details* → *Show private key*.
5. Selecionar a chave da rede Ethereum/EVM.
6. Autenticar com a senha da MetaMask.
7. Revelar a chave.
8. Copiar **diretamente** para o arquivo `.env` local (campo `BLOCKCHAIN_SEPOLIA_PRIVATE_KEY`).
9. Fechar a tela de revelação.
10. Limpar a área de transferência.

```text
NUNCA cole a chave privada no chat.
NUNCA inclua a chave em capturas de tela.
NUNCA faça commit do arquivo .env.
NUNCA use essa carteira para ativos reais.
```

---

## 6. Obtenção de SepoliaETH

SepoliaETH:

- paga gas na testnet;
- **não** é ETH da rede principal;
- **não** possui finalidade financeira real;
- **não** deve ser comprado;
- **não** deve ser enviado a quem promete “conversão”.

### Faucet utilizado na pesquisa

Link:

```text
https://sepolia-faucet.pk910.de/#/
```

Esse site utiliza trabalho computacional no navegador (mineração do faucet) para liberar SepoliaETH.

```text
Esse processo não significa que o usuário está validando blocos
da Ethereum Sepolia. Trata-se do mecanismo de prova de trabalho
adotado pelo próprio faucet para controlar a distribuição gratuita
de SepoliaETH.
```

### Procedimento

1. Acessar o faucet.
2. Colar o endereço público Ethereum.
3. Conferir os primeiros e últimos caracteres.
4. Iniciar o processo de mineração do faucet.
5. Observar hashrate e saldo acumulado no faucet (a interface pode rotular como *hasrate*, *balance*, *mining*, etc.).
6. Aguardar acumular saldo suficiente no contador do faucet.
7. Interromper a mineração (*Stop*).
8. Solicitar o resgate (*Claim*).
9. Aguardar a transação do faucet.
10. Conferir o saldo na MetaMask (rede Sepolia).
11. Conferir o saldo com Web3.py (script interativo, Teste 5).

Se a interface mudar, foque no objetivo de cada controle: campo de endereço, início/parada da mineração, acumulado e claim.

---

## 7. Configuração do RPC com Alchemy

1. Criar conta ou entrar na Alchemy.
2. Abrir o dashboard.
3. Acessar a aplicação do projeto.
4. Confirmar que **Ethereum Sepolia** está habilitada.
5. Abrir **Endpoints**.
6. Copiar o endpoint **HTTPS** (não WebSocket).
7. Colocar no `.env` em `BLOCKCHAIN_SEPOLIA_RPC_URL`.
8. Não publicar o token.
9. Testar conexão (script interativo ou trecho Python abaixo).
10. Conferir chain ID `11155111`.
11. Conferir bloco atual.
12. Conferir saldo.
13. Acompanhar métricas no painel.

### Painel da aplicação Alchemy utilizada na validação

```text
https://dashboard.alchemy.com/apps/u9v6kclm3xc3v78t/metrics
```

```text
O painel exige autenticação na conta Alchemy. A URL pode identificar
a aplicação do projeto, mas não substitui o endpoint RPC. A API key,
o token do RPC e a URL RPC completa não devem ser publicados.
```

Formato sanitizado permitido em documentação:

```env
BLOCKCHAIN_SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/SEU_TOKEN
```

Exemplo mascarado:

```env
BLOCKCHAIN_SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/********
```

---

## 8. Configuração do arquivo `.env`

Na raiz de `agrotrace-carbon-blockchain-service`, copie `.env.example` → `.env` e preencha:

```env
BLOCKCHAIN_DEFAULT_NETWORK_CODE=ethereum_sepolia

BLOCKCHAIN_SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/SEU_TOKEN
BLOCKCHAIN_SEPOLIA_CHAIN_ID=11155111
BLOCKCHAIN_SEPOLIA_PRIVATE_KEY=0xSUA_CHAVE_PRIVADA
BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS=0xENDERECO_DO_CONTRATO
BLOCKCHAIN_SEPOLIA_CONFIRMATIONS=1
BLOCKCHAIN_SEPOLIA_REQUEST_TIMEOUT_SECONDS=30
BLOCKCHAIN_SEPOLIA_RECEIPT_TIMEOUT_SECONDS=180
BLOCKCHAIN_SEPOLIA_EXPLORER_BASE_URL=https://sepolia.etherscan.io
```

Placeholders obrigatórios na documentação: `SEU_TOKEN`, `SUA_CHAVE_PRIVADA`, `ENDERECO_DO_CONTRATO`.

Durante a validação interativa, o script força `network_code=ethereum_sepolia` mesmo se o default do `.env` for outro valor.

### PowerShell — checagens sem revelar a chave

```powershell
# Variável existe? (não imprime o valor)
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('RPC', 'SIM' if os.getenv('BLOCKCHAIN_SEPOLIA_RPC_URL') else 'NAO'); print('KEY', 'SIM' if os.getenv('BLOCKCHAIN_SEPOLIA_PRIVATE_KEY') else 'NAO'); print('CONTRACT', 'SIM' if os.getenv('BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS') else 'NAO')"
```

```powershell
# Derivar endereço (não imprime a chave)
python -c "from dotenv import load_dotenv; import os; from eth_account import Account; load_dotenv(); k=os.environ['BLOCKCHAIN_SEPOLIA_PRIVATE_KEY']; k=k if k.startswith('0x') else '0x'+k; print(Account.from_key(k).address)"
```

```powershell
# RPC + chain ID + bloco
python -c "from dotenv import load_dotenv; import os; from web3 import Web3; load_dotenv(); u=os.environ['BLOCKCHAIN_SEPOLIA_RPC_URL']; w3=Web3(Web3.HTTPProvider(u)); print('connected', w3.is_connected()); print('chain', w3.eth.chain_id); print('block', w3.eth.block_number)"
```

```powershell
# Bytecode do contrato
python -c "from dotenv import load_dotenv; import os; from web3 import Web3; load_dotenv(); w3=Web3(Web3.HTTPProvider(os.environ['BLOCKCHAIN_SEPOLIA_RPC_URL'])); a=Web3.to_checksum_address(os.environ['BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS']); c=w3.eth.get_code(a); print('bytecode', len(c)>0, 'size', len(c))"
```

Nunca execute um comando que faça `print` da chave privada.

---

## 9. Instalação do Python e do ambiente virtual

1. Instale Python 3.11 ou superior (python.org).
2. No PowerShell, na raiz do módulo:

```powershell
cd agrotrace-carbon-blockchain-service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

Dependências relevantes: `web3`, `sqlalchemy`, `pydantic`, `pydantic-settings`, `python-dotenv` (transitiva), `eth_account` (via web3).

---

## 10. Instalação do Foundry no Windows

### PowerShell ≠ Git Bash ≠ WSL

- **PowerShell:** terminal padrão do Windows.
- **Git Bash:** shell do Git for Windows (aplicativo separado).
- **WSL:** Linux dentro do Windows (requer distribuição instalada).

Digitar `Git Bash` **dentro** do PowerShell **não** abre o Git Bash. Isso não é um comando do `git`.

Abra o Git Bash pelo menu Iniciar (“Git Bash”) ou pelo executável instalado com o Git for Windows.

### Instalação (no Git Bash)

```bash
curl -L https://foundry.paradigm.xyz | bash
source ~/.bashrc
foundryup
```

Verificação:

```bash
forge --version
cast --version
anvil --version
```

Se necessário, adicione `~/.foundry/bin` ao PATH.

### Erros comuns

| Erro | Causa / correção |
|---|---|
| `forge is not recognized` | Foundry não no PATH do PowerShell; use Git Bash ou ajuste PATH |
| `cast is not recognized` | Idem |
| `anvil is not recognized` | Idem |
| `WSL não possui distribuições` | WSL sem distro; instale Ubuntu ou use Git Bash |
| `git: 'Bash' is not a git command` | Você digitou algo como `git Bash` no PowerShell; abra o app Git Bash |

Documentação oficial Foundry: https://book.getfoundry.sh/

---

## 11. Compilação e testes do CarbonEvidenceRegistry

```powershell
cd contracts
forge build
forge test -vvv
forge fmt --check
```

- `forge build`: compila Solidity e gera artefatos em `contracts/out/`.
- `forge test -vvv`: roda testes do contrato com log detalhado.
- `forge fmt --check`: verifica formatação.

**Não faça deploy** se os testes estiverem falhando.

Exportar ABI para o módulo Python (se necessário):

```powershell
cd ..
python scripts/export_contract_abi.py
```

ABI usada pelo módulo:

```text
app/infrastructure/anchoring/contracts/CarbonEvidenceRegistry.abi.json
```

---

## 12. Deploy local com Anvil (opcional)

Útil para ensaio local, **não** substitui a validação Sepolia:

```bash
anvil
```

Em outro terminal, configure `BLOCKCHAIN_ANVIL_*` e faça deploy apontando para `http://127.0.0.1:8545`.

---

## 13. Deploy real na Ethereum Sepolia

### Dry run (sem `--broadcast`)

```powershell
forge script `
  script/DeployCarbonEvidenceRegistry.s.sol `
  --rpc-url $env:BLOCKCHAIN_SEPOLIA_RPC_URL `
  --private-key $env:BLOCKCHAIN_SEPOLIA_PRIVATE_KEY `
  -vvvv
```

### Deploy real (com `--broadcast`)

```powershell
forge script `
  script/DeployCarbonEvidenceRegistry.s.sol `
  --rpc-url $env:BLOCKCHAIN_SEPOLIA_RPC_URL `
  --private-key $env:BLOCKCHAIN_SEPOLIA_PRIVATE_KEY `
  --broadcast `
  -vvvv
```

```text
Sem --broadcast:
simulação local/dry run.

Com --broadcast:
transação realmente enviada à Sepolia.
```

### Onde achar o endereço do contrato

Arquivo típico:

```text
contracts/broadcast/DeployCarbonEvidenceRegistry.s.sol/11155111/run-latest.json
```

Campo:

```json
"contractAddress": "0x..."
```

Coloque em:

```env
BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS=0x...
```

Não confunda com:

- transaction hash;
- block hash;
- deployer address;
- carteira;
- chave privada.

Também registre dados públicos em `contracts/deployments/sepolia.json` quando aplicável.

---

## 14. Validação do contrato após o deploy

Resultado esperado:

```text
Chain ID: 11155111
Bytecode encontrado: True
Tamanho do bytecode: maior que 0
```

Consulte `owner()` e confirme:

```text
wallet_address == owner
```

O script interativo cobre esses passos nos Testes 4–8.

---

## 15. Seleção de pacote elegível

O pacote deve:

- existir no SQLite do blockchain-service;
- ter `package_hash` e `merkle_root`;
- estar ligado a um `anchor_request` com evento final:
  - `FINAL_ONTOLOGY_PUBLISHED`
  - `APPROVED_RESULT_PUBLISHED`
  - `APPROVED_RESULT_PUBLISHED_TO_ONTOLOGY`

`CALCULATION_APPROVED` **não** libera ancoragem.

Fluxo típico de criação (CLI do módulo):

```powershell
python -m app.interfaces.cli observe-events
python -m app.interfaces.cli process-anchor-requests
```

(Ajuste subcomandos conforme `--help` da CLI instalada.)

### Pacote de exemplo pelo script interativo

Se o banco estiver vazio, o Teste 10 oferece criar um **pacote de exemplo** local:

- evento `FINAL_ONTOLOGY_PUBLISHED`;
- hashes e Merkle Root pelos serviços oficiais do módulo;
- **não** envia transação Sepolia na criação;
- confirmação por ENTER (ou flag `--create-sample-package` + ENTER).

```powershell
python validar_sepolia_interativo.py --create-sample-package
```

Use isso para validar a ancoragem Sepolia quando ainda não houver pipeline completa no provenance.

---

## 16. Execução da validação interativa

```powershell
python validar_sepolia_interativo.py
```

```powershell
python validar_sepolia_interativo.py --package-id <UUID>
```

```powershell
python validar_sepolia_interativo.py --package-id <UUID> --query-only
```

```powershell
python validar_sepolia_interativo.py `
  --package-id <UUID> `
  --resume-transaction <TRANSACTION_HASH>
```

O script imprime:

```text
MODO DE EXECUÇÃO: ETHEREUM SEPOLIA REAL
```

Antes da ancoragem real, exige ENTER na confirmação destacada (contrato, carteira, pacote, hashes, saldo, chain ID).

Único teste que **pode consumir SepoliaETH**: Teste 15 (ancoragem), e somente após ENTER vazio.

---

## 17. Ancoragem pela CLI do módulo

```powershell
python -m app.interfaces.cli anchor-package `
  --package-id <UUID> `
  --network-code ethereum_sepolia
```

Campos esperados:

```text
transaction_hash
block_number
receipt_status
gas_used
anchoring_status
explorer_url
idempotent_reuse
```

Resultado válido:

```text
anchoring_status = confirmed
receipt_status = 1
```

---

## 18. Consulta pela CLI do módulo

```powershell
python -m app.interfaces.cli query-anchor `
  --package-id <UUID> `
  --network-code ethereum_sepolia
```

```text
found
evidence_key
package_hash
merkle_root
anchored_at
submitter
```

Resultado válido: `found = true`.

---

## 19. Verificação completa

```powershell
python -m app.interfaces.cli verify-anchor `
  --package-id <UUID> `
  --network-code ethereum_sepolia
```

```text
offchain_valid
onchain_found
package_hash_match
merkle_root_match
network_match
contract_match
overall_valid
```

Esperado: `overall_valid = true`.

---

## 20. Idempotência

Repetir a ancoragem do mesmo pacote na mesma rede **não** deve produzir nova transação.

Esperado:

```text
idempotent_reuse = true
```

Confirme:

- mesmo transaction hash;
- mesmo block number;
- nonce não consumido;
- nenhuma segunda transação no explorador para o mesmo `evidenceKey`.

Chave interna:

```text
idempotencyKey = SHA-256(network_code + ":" + package_hash)
```

---

## 21. Teste de adulteração

1. Copiar o payload canônico em memória (`deepcopy`).
2. Modificar a cópia (campo de teste).
3. Canonicalizar com o serviço oficial.
4. Recalcular SHA-256.
5. Comparar com o hash on-chain.
6. Observar divergência.
7. Confirmar que o original persistido continua intacto.

```text
original_match = true
tampered_match = false
overall_valid_original = true
```

---

## 22. Consulta no explorador

- Transação: `https://sepolia.etherscan.io/tx/<transaction_hash>`
- Contrato: `https://sepolia.etherscan.io/address/<contract_address>`
- Documentação Etherscan Sepolia: https://sepolia.etherscan.io/

---

## 23. Evidências geradas

Diretório:

```text
evidence/sepolia/interactive_validation_<timestamp>/
```

| Arquivo | Finalidade |
|---|---|
| `environment_validation.json` | Raiz / .env / variáveis (sem segredos) |
| `rpc_validation.json` | Conexão RPC sanitizada |
| `wallet_validation.json` | Endereço público e saldo |
| `contract_validation.json` | Bytecode / ABI / owner |
| `package_validation.json` | Pacote selecionado |
| `pre_anchor_query.json` | Consulta antes da ancoragem |
| `anchoring_result.json` | Resultado do caso de uso |
| `transaction_receipt.json` | Recibo Web3 |
| `contract_event.json` | Evento `EvidenceAnchored` |
| `post_anchor_query.json` | Consulta pós + Web3 independente |
| `integrity_verification.json` | VerifyAnchoredEvidence |
| `idempotency_validation.json` | Segunda ancoragem |
| `tampering_validation.json` | Adulteração em memória |
| `original_revalidation.json` | Original intacto |
| `public_links.json` | Links do explorador |
| `summary.json` | Resumo estruturado |
| `execution.log` | Log sanitizado |
| `VALIDACAO_EXECUTADA.md` | Relato humano após sucesso |

---

## 24. Resolução de erros comuns

### `BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS` vazio

- **Significado:** contrato não configurado.
- **Correção:** preencher após deploy; não inventar endereço.

### `Unknown format '', attempted to normalize to '0x'`

- **Causa:** endereço vazio passado ao Web3.
- **Correção:** valide o `.env` antes de conectar.

### RPC não conectado

- **Diagnóstico:** `w3.is_connected()` falso.
- **Correção:** token Alchemy, rede Sepolia, firewall.

### Chain ID diferente de 11155111

- **Causa:** endpoint de outra rede.
- **Correção:** use endpoint Sepolia.

### Carteira sem saldo

- **Causa:** faucet não creditou.
- **Correção:** obter SepoliaETH; não ancore com saldo zero.

### Carteira diferente do owner

- **Causa:** chave ≠ deployer.
- **Correção:** use a chave do owner ou redeploy.

### Contrato sem bytecode

- **Causa:** endereço errado ou deploy sem `--broadcast`.
- **Correção:** confira `run-latest.json`.

### ABI não encontrada / incompatível

- **Correção:** `forge build` + `scripts/export_contract_abi.py`.

### Package ID inexistente

- **Correção:** construir pacote antes; listar candidatos no script.

### Gate de publicação final negado / `CALCULATION_APPROVED`

- **Causa:** evento preliminar.
- **Correção:** só eventos finais elegíveis.

### Timeout aguardando recibo

- **Ação:** salve o `transaction_hash`; **não** reenvie; use `--resume-transaction`.

### Transação revertida / `NotAuthorized` / `EvidenceAlreadyAnchored`

- **Diagnóstico:** logs do recibo / erro do provider.
- **Correção:** owner, evidência já ancorada (idempotência), parâmetros não-zero.

### `DuplicateEvidenceError`

- **Significado:** já existe on-chain.
- **Correção:** consulte; não force nova tx.

### `Nonce too low` / `Replacement transaction underpriced` / `Insufficient funds`

- **Causa:** nonce/gas/saldo.
- **Correção:** aguarde pendências; ajuste gas; abasteça faucet. Não dispare retries cegos.

### Hash / Merkle Root divergente

- **Causa:** pacote alterado ou canonicalização diferente.
- **Correção:** use apenas serviços oficiais do módulo; não reimplemente hash.

---

## 25. Proteção de segredos

Nunca versionar:

- `.env`
- chave privada
- mnemonic / frase de recuperação
- URL RPC com token
- transação assinada bruta

Pode versionar/publicar:

- endereço público da carteira
- endereço do contrato
- transaction hash / block number
- package hash / merkle root / evidence key
- links do explorador

---

## 26. Limpeza e encerramento

1. Remova a chave da área de transferência.
2. Não compartilhe o diretório `evidence/` se contiver dados sensíveis de negócio (os hashes em si são públicos na cadeia).
3. Desative a extensão MetaMask quando não estiver em uso.
4. Mantenha SepoliaETH apenas o necessário para testes.

---

## 27. Checklist final reproduzível

- [ ] MetaMask instalada; conta `AgroTrace Sepolia`; rede Sepolia ativa
- [ ] Frase de recuperação offline; chave apenas no `.env` local
- [ ] SepoliaETH obtido via faucet (pk910)
- [ ] Alchemy Sepolia HTTPS configurado (token não publicado)
- [ ] Foundry: `forge`/`cast`/`anvil` ok
- [ ] `forge build` e `forge test` passando
- [ ] Deploy Sepolia com `--broadcast`
- [ ] `BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS` preenchido
- [ ] Bytecode e `owner()` validados
- [ ] Pacote elegível com publicação final
- [ ] `python validar_sepolia_interativo.py` concluído com sucesso
- [ ] Explorador mostra a transação
- [ ] Idempotência confirmada
- [ ] Adulteração em memória falha como esperado
- [ ] Evidências JSON geradas sem segredos

---

## Links utilizados no ambiente da pesquisa

| Recurso | URL / nota |
|---|---|
| Faucet Sepolia (PoW no navegador) | https://sepolia-faucet.pk910.de/#/ |
| Painel Alchemy (métricas; exige login) | https://dashboard.alchemy.com/apps/u9v6kclm3xc3v78t/metrics |
| Formato RPC Alchemy (placeholder) | `https://eth-sepolia.g.alchemy.com/v2/SEU_TOKEN` |
| Explorador Sepolia | https://sepolia.etherscan.io/ |
| MetaMask (oficial) | https://metamask.io/ |
| Foundry Book | https://book.getfoundry.sh/ |
| Alchemy docs | https://docs.alchemy.com/ |

### Referências oficiais sugeridas

- Criar carteira MetaMask / redes de teste: documentação MetaMask (*Get started*, *Networks*).
- Exportar chave privada: MetaMask *Account details* (apenas localmente).
- Criar app Alchemy e obter endpoint HTTPS Sepolia: dashboard Alchemy → Apps → Endpoints.
- Instalar Foundry e deploy com `forge script`: Foundry Book.
- Consultar tx/contrato: Etherscan Sepolia.

---

## Interpretação de PASSOU / FALHOU / AVISO / IGNORADO

Ver [docs/validacao_interativa_sepolia.md](docs/validacao_interativa_sepolia.md).

---

## Relacionamento com a arquitetura AgroTrace

- **traceability-service:** linhagem 1–20; não ancora.
- **blockchain-service:** só após publicação final.
- Hash de arquivo bruto ≠ ancoragem.
- `SimulatedAnchorProvider` / Anvil ≠ Sepolia real.

Para a dissertação, preserve evidências do diretório `evidence/sepolia/...` e o arquivo `VALIDACAO_EXECUTADA.md` gerado após sucesso.
