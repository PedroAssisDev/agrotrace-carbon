# Evidências de validação blockchain

## Política

Os artefatos sob `evidence/sepolia/` são **evidência acadêmica declarada** da
validação interativa na rede Ethereum Sepolia (execuções históricas do
protótipo AgroMRV-Flow). Permanecem versionados de propósito.

### O que contêm

- Endereços públicos de carteira e contrato
- Hashes de transação e links Etherscan
- RPC e chaves **já redigidos** (`********`)

### O que **não** contêm

- Chaves privadas em claro
- Tokens de RPC em claro

### Distribuição

- Adequados para clone Git e para o pacote `software-release/`
- O scanner `frontend/scripts/scan_secrets.py` inspeciona este diretório e
  trata caminhos `evidence/sepolia/` como allowlist acadêmica (endereços
  públicos / tokens redigidos)
- Novas execuções locais devem continuar gerando artefatos sob `evidence/`
  (gitignored para runs futuros); apenas conjuntos revisados entram no índice

### Relação com `contracts/deployments/sepolia.json`

O arquivo `contracts/deployments/sepolia.json` registra o estado do
*script de deploy Foundry* do repositório (`status: not_deployed` quando o
deploy automatizado não foi commitado). A evidência em `evidence/sepolia/`
documenta validações contra um contrato já implantado em ambiente do autor.
Não há contradição: são artefatos de propósitos distintos.
