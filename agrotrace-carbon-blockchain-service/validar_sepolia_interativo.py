"""Validação interativa e segura da integração Ethereum Sepolia.

Executa, com confirmação explícita do usuário (ENTER), checagens de
infraestrutura, pacote elegível, gate de publicação final, ancoragem real,
consulta on-chain, verificação, idempotência e adulteração controlada.

Uso (a partir da raiz do módulo)::

    python validar_sepolia_interativo.py
    python validar_sepolia_interativo.py --package-id <UUID>
    python validar_sepolia_interativo.py --package-id <UUID> --query-only
    python validar_sepolia_interativo.py --package-id <UUID> --resume-transaction <TX_HASH>

Nunca imprime chave privada, RPC com token, mnemonic ou conteúdo do .env.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import logging
import os
import re
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class UserAbortedError(SystemExit):
    """Usuário encerrou digitando texto em vez de ENTER."""

    def __init__(self) -> None:
        super().__init__(0)


class CriticalValidationError(Exception):
    """Falha que interrompe a validação."""

    def __init__(self, message: str, *, recommendation: str = "") -> None:
        super().__init__(message)
        self.recommendation = recommendation


class NonCriticalValidationError(Exception):
    """Falha ou aviso que não encerra necessariamente o fluxo."""


# ---------------------------------------------------------------------------
# Status / results
# ---------------------------------------------------------------------------


class TestStatus(str, Enum):
    PASSED = "PASSOU"
    FAILED = "FALHOU"
    WARNING = "AVISO"
    SKIPPED = "IGNORADO"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    details: dict[str, Any] = field(default_factory=dict)
    message: str = ""


@dataclass
class TestDefinition:
    number: int
    name: str
    objective: str
    action: str
    expected: str


@dataclass
class ValidationContext:
    root: Path
    evidence_dir: Path
    env_path: Path
    args: argparse.Namespace
    results: list[TestResult] = field(default_factory=list)
    logger: logging.Logger | None = None

    # Filled during tests
    rpc_url: str = ""
    chain_id: int = 11155111
    private_key_configured: bool = False
    contract_address: str = ""
    wallet_address: str = ""
    balance_wei: int = 0
    confirmations: int = 1
    request_timeout: float = 30.0
    receipt_timeout: float = 180.0
    explorer_base: str = "https://sepolia.etherscan.io"
    w3: Any = None
    abi: list[dict[str, Any]] = field(default_factory=list)
    abi_path: Path | None = None
    contract: Any = None
    container: Any = None
    settings: Any = None
    package_id: UUID | None = None
    package: Any = None
    anchor_request: Any = None
    source_event_type: str = ""
    package_hash: str = ""
    merkle_root: str = ""
    evidence_key: str = ""
    idempotency_key: str = ""
    pre_query_found: bool = False
    transaction_hash: str | None = None
    block_number: int | None = None
    anchoring_result: dict[str, Any] = field(default_factory=dict)
    receipt: dict[str, Any] = field(default_factory=dict)
    event_data: dict[str, Any] = field(default_factory=dict)
    post_query: dict[str, Any] = field(default_factory=dict)
    verify_result: dict[str, Any] = field(default_factory=dict)
    idempotent_reuse: bool = False
    resume_mode: bool = False
    query_only: bool = False


SEPOLIA_CHAIN_ID = 11155111
NETWORK_CODE = "ethereum_sepolia"
SECRET_KEY_PATTERN = re.compile(
    r"(PRIVATE_KEY|MNEMONIC|SECRET|TOKEN|API_KEY|PASSWORD|RPC_URL|raw_transaction|signed)",
    re.IGNORECASE,
)

REQUIRED_ENV_VARS = [
    "BLOCKCHAIN_DEFAULT_NETWORK_CODE",
    "BLOCKCHAIN_SEPOLIA_RPC_URL",
    "BLOCKCHAIN_SEPOLIA_CHAIN_ID",
    "BLOCKCHAIN_SEPOLIA_PRIVATE_KEY",
    "BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS",
    "BLOCKCHAIN_SEPOLIA_CONFIRMATIONS",
    "BLOCKCHAIN_SEPOLIA_REQUEST_TIMEOUT_SECONDS",
    "BLOCKCHAIN_SEPOLIA_RECEIPT_TIMEOUT_SECONDS",
    "BLOCKCHAIN_SEPOLIA_EXPLORER_BASE_URL",
]


# ---------------------------------------------------------------------------
# Sanitization
# ---------------------------------------------------------------------------


def redact_secret(value: str | None) -> str:
    if value is None or value == "":
        return "(vazio)"
    if len(value) <= 8:
        return "********"
    return value[:4] + "********" + value[-4:]


def sanitize_rpc_url(url: str | None) -> str:
    if not url:
        return "(ausente)"
    try:
        from urllib.parse import urlsplit, urlunsplit

        parts = urlsplit(url)
        path = parts.path or ""
        if "/v2/" in path or "/v3/" in path or len(path) > 20:
            segments = path.strip("/").split("/")
            if len(segments) >= 2:
                segments[-1] = "********"
                path = "/" + "/".join(segments)
            else:
                path = "/********"
        elif path and path != "/":
            path = "/********"
        query = "********" if parts.query else ""
        return urlunsplit((parts.scheme, parts.netloc, path, query, ""))
    except Exception:
        return "https://********"


def sanitize_mapping(data: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in data.items():
        key_str = str(key)
        if SECRET_KEY_PATTERN.search(key_str):
            if "RPC" in key_str.upper() and isinstance(value, str):
                result[key_str] = sanitize_rpc_url(value)
            else:
                result[key_str] = "********"
        elif isinstance(value, dict):
            result[key_str] = sanitize_mapping(value)
        elif isinstance(value, list):
            result[key_str] = [
                sanitize_mapping(item) if isinstance(item, dict) else item for item in value
            ]
        elif isinstance(value, str) and (
            "alchemy.com" in value.lower() or "infura.io" in value.lower()
        ):
            result[key_str] = sanitize_rpc_url(value)
        else:
            result[key_str] = value
    return result


def safe_serialize(obj: Any) -> Any:
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, bytes):
        return "0x" + obj.hex()
    if isinstance(obj, dict):
        return sanitize_mapping({str(k): safe_serialize(v) for k, v in obj.items()})
    if isinstance(obj, (list, tuple)):
        return [safe_serialize(item) for item in obj]
    if hasattr(obj, "__dict__"):
        return safe_serialize(vars(obj))
    return str(obj)


def is_valid_eth_address(address: str) -> bool:
    if not isinstance(address, str):
        return False
    cleaned = address.strip()
    if not cleaned.startswith("0x") or len(cleaned) != 42:
        return False
    try:
        int(cleaned[2:], 16)
        return True
    except ValueError:
        return False


def is_valid_hash_32(value: str | None) -> bool:
    if not value or not isinstance(value, str):
        return False
    cleaned = value.lower().strip()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    if len(cleaned) != 64:
        return False
    try:
        return len(bytes.fromhex(cleaned)) == 32
    except ValueError:
        return False


def normalize_private_key_hex(key: str) -> str:
    cleaned = key.strip()
    if cleaned.startswith("0x"):
        cleaned = cleaned[2:]
    return cleaned


def private_key_has_32_bytes(key: str) -> bool:
    cleaned = normalize_private_key_hex(key)
    if len(cleaned) != 64:
        return False
    try:
        return len(bytes.fromhex(cleaned)) == 32
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Interaction
# ---------------------------------------------------------------------------


def aguardar_enter(mensagem: str) -> None:
    resposta = input(mensagem)
    if resposta != "":
        print("Execução encerrada pelo usuário.")
        raise UserAbortedError()


def pause_before_test(test: TestDefinition) -> None:
    print()
    print("=" * 60)
    print(f"TESTE {test.number} — {test.name}")
    print("=" * 60)
    print()
    print("Objetivo:")
    print(test.objective)
    print()
    print("O que será executado:")
    print(test.action)
    print()
    print("Resultado esperado:")
    print(test.expected)
    print()
    aguardar_enter(
        "Pressione ENTER para executar este teste ou digite qualquer coisa para encerrar: "
    )


def pause_after_test() -> None:
    print()
    aguardar_enter(
        "Pressione ENTER para continuar para o próximo teste ou digite qualquer coisa para encerrar: "
    )


def print_status(status: TestStatus, extra: str = "") -> None:
    label = f"[{status.value}]" if not extra else f"[{status.value}{extra}]"
    print(label)


# ---------------------------------------------------------------------------
# Logging / evidence
# ---------------------------------------------------------------------------


class SanitizingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        original = super().format(record)
        # Strip obvious private-key shaped tokens from log lines
        redacted = re.sub(r"0x[a-fA-F0-9]{64}", "0x********", original)
        redacted = re.sub(
            r"(https?://[^/\s]+/(?:v2|v3)/)[A-Za-z0-9_\-]+",
            r"\1********",
            redacted,
        )
        return redacted


def setup_logger(evidence_dir: Path) -> logging.Logger:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("sepolia_validation")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = SanitizingFormatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.FileHandler(evidence_dir / "execution.log", encoding="utf-8")
    fh.setFormatter(fmt)
    fh.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(SanitizingFormatter("%(message)s"))
    ch.setLevel(logging.INFO)
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def write_evidence(evidence_dir: Path, filename: str, payload: dict[str, Any], status: str) -> Path:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    body = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status,
        **safe_serialize(payload),
    }
    path = evidence_dir / filename
    path.write_text(json.dumps(body, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return path


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


# ---------------------------------------------------------------------------
# Args / root / deps
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validação interativa completa da integração Ethereum Sepolia "
            "(ancoragem real mediante ENTER)."
        )
    )
    parser.add_argument(
        "--package-id",
        default=None,
        help="UUID do pacote de evidência (opcional; senão lista candidatos).",
    )
    parser.add_argument(
        "--query-only",
        action="store_true",
        help="Apenas consultas; não envia transação de ancoragem.",
    )
    parser.add_argument(
        "--resume-transaction",
        default=None,
        metavar="TX_HASH",
        help="Retoma validação a partir de um transaction hash já enviado (não reenvia).",
    )
    parser.add_argument(
        "--create-sample-package",
        action="store_true",
        help=(
            "Se não houver pacote elegível (e --package-id não for informado), "
            "cria um pacote de exemplo no banco local após confirmação ENTER."
        ),
    )
    return parser.parse_args(argv)


def detect_project_root(script_path: Path | None = None) -> Path:
    script = (script_path or Path(__file__)).resolve()
    root = script.parent
    required = ["pyproject.toml", "app", "contracts", "schemas", "scripts"]
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        raise CriticalValidationError(
            f"Raiz do módulo inválida em {root}. Ausentes: {missing}",
            recommendation="Execute o script a partir da raiz de agrotrace-carbon-blockchain-service.",
        )
    return root


def check_dependencies() -> list[str]:
    missing: list[str] = []
    suggestions = {
        "dotenv": 'python -m pip install python-dotenv  (ou python -m pip install -e ".[dev]")',
        "web3": 'python -m pip install -e ".[dev]"',
        "eth_account": 'python -m pip install -e ".[dev]"',
        "sqlalchemy": 'python -m pip install -e ".[dev]"',
        "pydantic": 'python -m pip install -e ".[dev]"',
    }
    for name in ("dotenv", "web3", "eth_account", "sqlalchemy", "pydantic"):
        mod = "dotenv" if name == "dotenv" else name
        try:
            if mod == "dotenv":
                __import__("dotenv")
            else:
                __import__(mod)
        except ImportError:
            print(f"Dependência ausente: {name}")
            print(f"Comando sugerido: {suggestions[name]}")
            missing.append(name)
    return missing


# ---------------------------------------------------------------------------
# Helpers for packages / web3
# ---------------------------------------------------------------------------


def list_eligible_packages(container: Any, limit: int = 20) -> list[dict[str, Any]]:
    from app.infrastructure.db.models import AnchorRequestModel, EvidencePackageModel
    from app.shared.constants import FINAL_PUBLICATION_EVENT_TYPES

    session = container.session_factory()
    try:
        rows = (
            session.query(EvidencePackageModel, AnchorRequestModel)
            .join(
                AnchorRequestModel,
                EvidencePackageModel.anchor_request_id == AnchorRequestModel.anchor_request_id,
            )
            .filter(AnchorRequestModel.source_event_type.in_(tuple(FINAL_PUBLICATION_EVENT_TYPES)))
            .filter(EvidencePackageModel.package_hash.isnot(None))
            .filter(EvidencePackageModel.merkle_root.isnot(None))
            .filter(EvidencePackageModel.package_hash != "")
            .filter(EvidencePackageModel.merkle_root != "")
            .order_by(EvidencePackageModel.created_at.desc())
            .limit(limit)
            .all()
        )
        out: list[dict[str, Any]] = []
        for pkg, req in rows:
            out.append(
                {
                    "evidence_package_id": pkg.evidence_package_id,
                    "status": pkg.status,
                    "package_hash": pkg.package_hash,
                    "merkle_root": pkg.merkle_root,
                    "event_type": req.source_event_type,
                    "period_start": pkg.period_start,
                    "period_end": pkg.period_end,
                }
            )
        return out
    finally:
        session.close()


def count_transactions_for_package(container: Any, package_id: UUID) -> int:
    from app.infrastructure.db.models import BlockchainTransactionModel

    session = container.session_factory()
    try:
        return (
            session.query(BlockchainTransactionModel)
            .filter(BlockchainTransactionModel.evidence_package_id == str(package_id))
            .count()
        )
    finally:
        session.close()


def load_abi(root: Path) -> tuple[Path, list[dict[str, Any]]]:
    preferred = (
        root
        / "app"
        / "infrastructure"
        / "anchoring"
        / "contracts"
        / "CarbonEvidenceRegistry.abi.json"
    )
    if not preferred.exists():
        raise CriticalValidationError(
            f"ABI não encontrada: {preferred}",
            recommendation="Execute scripts/export_contract_abi.py após forge build.",
        )
    raw = json.loads(preferred.read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "abi" in raw:
        abi = raw["abi"]
    else:
        abi = raw
    if not isinstance(abi, list):
        raise CriticalValidationError(
            "ABI inválida: esperado lista ou objeto com chave 'abi'.",
            recommendation="Regenere a ABI a partir do artefato Foundry.",
        )
    return preferred, abi


def abi_has_function(abi: list[dict[str, Any]], name: str) -> bool:
    return any(entry.get("type") == "function" and entry.get("name") == name for entry in abi)


def abi_has_event(abi: list[dict[str, Any]], name: str) -> bool:
    return any(entry.get("type") == "event" and entry.get("name") == name for entry in abi)


def explorer_tx_url(base: str, tx_hash: str) -> str:
    return f"{base.rstrip('/')}/tx/{tx_hash}"


def explorer_address_url(base: str, address: str) -> str:
    return f"{base.rstrip('/')}/address/{address}"


def hex_eq(a: str | None, b: str | None) -> bool:
    if a is None or b is None:
        return False
    return a.lower().strip() == b.lower().strip()


def bytes32_hex_from_value(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return "0x" + bytes(value).hex()
    if isinstance(value, str):
        return value if value.startswith("0x") else "0x" + value
    return str(value)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_01_root(ctx: ValidationContext) -> TestResult:
    cwd = Path.cwd().resolve()
    script_dir = Path(__file__).resolve().parent
    found = {
        "pyproject.toml": (ctx.root / "pyproject.toml").exists(),
        "app/": (ctx.root / "app").is_dir(),
        "contracts/": (ctx.root / "contracts").is_dir(),
        "schemas/": (ctx.root / "schemas").is_dir(),
        "scripts/": (ctx.root / "scripts").is_dir(),
    }
    details = {
        "Diretório atual": str(cwd),
        "Diretório do script": str(script_dir),
        "Raiz detectada": str(ctx.root),
        "Arquivos obrigatórios encontrados": found,
    }
    for key, value in details.items():
        print(f"{key}: {value}")
    if not all(found.values()):
        raise CriticalValidationError(
            "Arquivos obrigatórios da raiz ausentes.",
            recommendation="Confirme que está na raiz do agrotrace-carbon-blockchain-service.",
        )
    write_evidence(ctx.evidence_dir, "environment_validation.json", details, TestStatus.PASSED.value)
    return TestResult("Raiz do módulo", TestStatus.PASSED, details)


def test_02_env(ctx: ValidationContext) -> TestResult:
    env_path = ctx.root / ".env"
    ctx.env_path = env_path
    exists = env_path.exists()
    readable = False
    if exists:
        try:
            _ = env_path.read_text(encoding="utf-8")
            readable = True
        except OSError:
            readable = False
    print(f"Arquivo encontrado: {'SIM' if exists else 'NÃO'}")
    print(f"Caminho absoluto: {env_path.resolve()}")
    print(f"Arquivo legível: {'SIM' if readable else 'NÃO'}")
    if not exists:
        raise CriticalValidationError(
            "Arquivo .env ausente.",
            recommendation="Copie .env.example para .env e preencha as variáveis Sepolia.",
        )
    if not readable:
        raise CriticalValidationError(
            "Arquivo .env não é legível.",
            recommendation="Verifique permissões do arquivo .env.",
        )
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=env_path, override=True)
    details = {
        "Arquivo encontrado": True,
        "Caminho absoluto": str(env_path.resolve()),
        "Arquivo legível": True,
        "conteudo": "(omitido por segurança)",
    }
    write_evidence(ctx.evidence_dir, "environment_validation.json", details, TestStatus.PASSED.value)
    return TestResult("Arquivo .env", TestStatus.PASSED, details)


def test_03_vars(ctx: ValidationContext) -> TestResult:
    status_map: dict[str, str] = {}
    for name in REQUIRED_ENV_VARS:
        value = os.environ.get(name, "")
        status_map[name] = "CONFIGURADA" if value.strip() else "AUSENTE"
        print(f"{name}: {status_map[name]}")

    rpc = os.environ.get("BLOCKCHAIN_SEPOLIA_RPC_URL", "").strip()
    chain_raw = os.environ.get("BLOCKCHAIN_SEPOLIA_CHAIN_ID", "").strip()
    key = os.environ.get("BLOCKCHAIN_SEPOLIA_PRIVATE_KEY", "").strip()
    contract = os.environ.get("BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS", "").strip()
    default_net = os.environ.get("BLOCKCHAIN_DEFAULT_NETWORK_CODE", "").strip()
    conf_raw = os.environ.get("BLOCKCHAIN_SEPOLIA_CONFIRMATIONS", "1").strip()
    req_to = os.environ.get("BLOCKCHAIN_SEPOLIA_REQUEST_TIMEOUT_SECONDS", "30").strip()
    rec_to = os.environ.get("BLOCKCHAIN_SEPOLIA_RECEIPT_TIMEOUT_SECONDS", "180").strip()
    explorer = os.environ.get(
        "BLOCKCHAIN_SEPOLIA_EXPLORER_BASE_URL", "https://sepolia.etherscan.io"
    ).strip()

    critical_msgs: list[str] = []
    if not rpc:
        critical_msgs.append("BLOCKCHAIN_SEPOLIA_RPC_URL ausente")
    elif not (rpc.startswith("http://") or rpc.startswith("https://")):
        critical_msgs.append("BLOCKCHAIN_SEPOLIA_RPC_URL deve começar com http:// ou https://")
    if not key:
        critical_msgs.append("BLOCKCHAIN_SEPOLIA_PRIVATE_KEY ausente")
    elif not private_key_has_32_bytes(key):
        critical_msgs.append("BLOCKCHAIN_SEPOLIA_PRIVATE_KEY inválida (esperado 32 bytes)")
    if not contract:
        critical_msgs.append("BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS ausente")
    elif not is_valid_eth_address(contract):
        critical_msgs.append("BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS inválido")
    try:
        chain_id = int(chain_raw)
    except ValueError:
        chain_id = -1
        critical_msgs.append("BLOCKCHAIN_SEPOLIA_CHAIN_ID inválido")
    if chain_id != SEPOLIA_CHAIN_ID:
        critical_msgs.append(f"BLOCKCHAIN_SEPOLIA_CHAIN_ID deve ser {SEPOLIA_CHAIN_ID}")

    print(f"Chave privada configurada: {'SIM' if bool(key) else 'NÃO'}")
    print(f"Tamanho válido: {'SIM' if key and private_key_has_32_bytes(key) else 'NÃO'}")

    if critical_msgs:
        raise CriticalValidationError(
            "; ".join(critical_msgs),
            recommendation="Corrija o .env com valores Sepolia válidos (sem publicar segredos).",
        )

    ctx.rpc_url = rpc
    ctx.chain_id = chain_id
    ctx.private_key_configured = True
    ctx.contract_address = contract
    ctx.confirmations = max(0, int(conf_raw or "1"))
    ctx.request_timeout = float(req_to or "30")
    ctx.receipt_timeout = float(rec_to or "180")
    ctx.explorer_base = explorer or "https://sepolia.etherscan.io"

    known_nets = {"ethereum_sepolia", "local_simulated", "anvil_local"}
    if default_net and default_net not in known_nets:
        print(f"[AVISO] BLOCKCHAIN_DEFAULT_NETWORK_CODE desconhecido: {default_net}")

    if ctx.request_timeout <= 0 or ctx.receipt_timeout <= 0:
        raise CriticalValidationError(
            "Timeouts devem ser números positivos.",
            recommendation="Ajuste REQUEST/RECEIPT_TIMEOUT_SECONDS no .env.",
        )

    details = {
        "variaveis": status_map,
        "rpc_sanitizado": sanitize_rpc_url(rpc),
        "chain_id": chain_id,
        "contract_address": contract,
        "default_network_code": default_net,
        "confirmations": ctx.confirmations,
        "request_timeout": ctx.request_timeout,
        "receipt_timeout": ctx.receipt_timeout,
        "chave_privada_configurada": True,
        "tamanho_chave_valido": True,
    }
    write_evidence(ctx.evidence_dir, "environment_validation.json", details, TestStatus.PASSED.value)
    return TestResult("Configuração", TestStatus.PASSED, details)


def test_04_rpc(ctx: ValidationContext) -> TestResult:
    from web3 import Web3

    w3 = Web3(
        Web3.HTTPProvider(
            ctx.rpc_url,
            request_kwargs={"timeout": ctx.request_timeout},
        )
    )
    try:
        from web3.middleware import ExtraDataToPOAMiddleware

        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    except Exception:
        pass

    connected = bool(w3.is_connected())
    if not connected:
        raise CriticalValidationError(
            "RPC indisponível.",
            recommendation="Verifique BLOCKCHAIN_SEPOLIA_RPC_URL e a API key do provedor.",
        )
    chain_id = int(w3.eth.chain_id)
    if chain_id != SEPOLIA_CHAIN_ID:
        raise CriticalValidationError(
            f"Chain ID incorreto: {chain_id}",
            recommendation=f"Use a rede Sepolia (chain_id={SEPOLIA_CHAIN_ID}).",
        )
    block = w3.eth.get_block("latest")
    client_version = ""
    try:
        client_version = w3.client_version
    except Exception:
        try:
            client_version = w3.provider.make_request("web3_clientVersion", [])  # type: ignore[attr-defined]
        except Exception:
            client_version = "(indisponível)"

    ts = block.get("timestamp")
    details = {
        "RPC sanitizado": sanitize_rpc_url(ctx.rpc_url),
        "Conectado": connected,
        "Client version": str(client_version),
        "Chain ID": chain_id,
        "Bloco atual": int(block["number"]),
        "Timestamp do bloco mais recente": int(ts) if ts is not None else None,
    }
    for key, value in details.items():
        print(f"{key}: {value}")
    print("Conectado: True")
    print(f"Chain ID: {SEPOLIA_CHAIN_ID}")
    ctx.w3 = w3
    write_evidence(ctx.evidence_dir, "rpc_validation.json", details, TestStatus.PASSED.value)
    return TestResult("RPC Sepolia", TestStatus.PASSED, details)


def test_05_wallet(ctx: ValidationContext) -> TestResult:
    from eth_account import Account
    from web3 import Web3

    key = os.environ.get("BLOCKCHAIN_SEPOLIA_PRIVATE_KEY", "").strip()
    key_hex = key if key.startswith("0x") else "0x" + key
    account = Account.from_key(key_hex)
    address = account.address
    checksum_ok = Web3.is_checksum_address(address) or address == Web3.to_checksum_address(address)
    balance = int(ctx.w3.eth.get_balance(address))
    nonce_latest = int(ctx.w3.eth.get_transaction_count(address, "latest"))
    nonce_pending = int(ctx.w3.eth.get_transaction_count(address, "pending"))
    eth_balance = float(Web3.from_wei(balance, "ether"))

    print(f"Endereço público: {address}")
    print(f"Checksum válido: {checksum_ok}")
    print(f"Saldo em wei: {balance}")
    print(f"Saldo em SepoliaETH: {eth_balance}")
    print(f"Nonce latest: {nonce_latest}")
    print(f"Nonce pending: {nonce_pending}")
    print("Chave privada configurada: SIM")
    print(f"Tamanho válido: SIM")
    print(f"Endereço derivado: {address}")

    ctx.wallet_address = address
    ctx.balance_wei = balance
    status = TestStatus.PASSED
    if balance == 0:
        status = TestStatus.WARNING
        print("AVISO CRÍTICO: saldo zero — ancoragem real falhará por falta de gas.")

    details = {
        "Endereço público": address,
        "Checksum válido": checksum_ok,
        "Saldo em wei": balance,
        "Saldo em SepoliaETH": eth_balance,
        "Nonce latest": nonce_latest,
        "Nonce pending": nonce_pending,
    }
    write_evidence(ctx.evidence_dir, "wallet_validation.json", details, status.value)
    # Also record Saldo row for the final summary table
    return TestResult("Carteira", status, details)


def test_06_contract(ctx: ValidationContext) -> TestResult:
    from web3 import Web3

    address = Web3.to_checksum_address(ctx.contract_address)
    code = ctx.w3.eth.get_code(address)
    code_bytes = bytes(code) if code is not None else b""
    found = len(code_bytes) > 0
    bytecode_hash = "0x" + hashlib.sha256(code_bytes).hexdigest() if found else None
    print(f"Endereço: {address}")
    print(f"Checksum: {address}")
    print(f"Bytecode encontrado: {found}")
    print(f"Tamanho do bytecode: {len(code_bytes)}")
    if bytecode_hash:
        print(f"Hash do bytecode: {bytecode_hash}")
    if not found:
        raise CriticalValidationError(
            "Contrato sem bytecode no endereço configurado.",
            recommendation="Confirme BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS após deploy com --broadcast.",
        )
    ctx.contract_address = address
    details = {
        "Endereço": address,
        "Checksum": address,
        "Bytecode encontrado": True,
        "Tamanho do bytecode": len(code_bytes),
        "Hash do bytecode": bytecode_hash,
    }
    write_evidence(ctx.evidence_dir, "contract_validation.json", details, TestStatus.PASSED.value)
    return TestResult("Contrato", TestStatus.PASSED, details)


def test_07_abi(ctx: ValidationContext) -> TestResult:
    path, abi = load_abi(ctx.root)
    required_fns = ["owner", "anchorEvidence", "getEvidence", "evidenceExists"]
    missing_fns = [name for name in required_fns if not abi_has_function(abi, name)]
    has_event = abi_has_event(abi, "EvidenceAnchored")
    functions = [e["name"] for e in abi if e.get("type") == "function" and e.get("name")]
    events = [e["name"] for e in abi if e.get("type") == "event" and e.get("name")]
    print(f"Caminho da ABI: {path}")
    print(f"Quantidade de entradas: {len(abi)}")
    print(f"Funções encontradas: {functions}")
    print(f"Eventos encontrados: {events}")
    if missing_fns or not has_event:
        raise CriticalValidationError(
            f"ABI incompatível. Funções ausentes={missing_fns}, EvidenceAnchored={has_event}",
            recommendation="Regenere CarbonEvidenceRegistry.abi.json a partir do contrato.",
        )
    ctx.abi = abi
    ctx.abi_path = path
    details = {
        "Caminho da ABI": str(path),
        "Quantidade de entradas": len(abi),
        "Funções encontradas": functions,
        "Eventos encontrados": events,
    }
    write_evidence(ctx.evidence_dir, "contract_validation.json", {**details}, TestStatus.PASSED.value)
    return TestResult("ABI", TestStatus.PASSED, details)


def test_08_owner(ctx: ValidationContext) -> TestResult:
    from web3 import Web3

    contract = ctx.w3.eth.contract(
        address=Web3.to_checksum_address(ctx.contract_address),
        abi=ctx.abi,
    )
    owner = contract.functions.owner().call()
    authorized = owner.lower() == ctx.wallet_address.lower()
    print(f"Carteira configurada: {ctx.wallet_address}")
    print(f"Owner do contrato: {owner}")
    print(f"Carteira autorizada: {authorized}")
    if not authorized:
        raise CriticalValidationError(
            "Carteira não é proprietária do contrato.",
            recommendation="Use a chave do deployer/owner ou faça deploy com a carteira correta.",
        )
    ctx.contract = contract
    details = {
        "Carteira configurada": ctx.wallet_address,
        "Owner do contrato": owner,
        "Carteira autorizada": True,
    }
    write_evidence(ctx.evidence_dir, "contract_validation.json", details, TestStatus.PASSED.value)
    return TestResult("Owner", TestStatus.PASSED, details)


def test_09_module(ctx: ValidationContext) -> TestResult:
    from app.application.container import ServiceContainer, init_database
    from app.infrastructure.anchoring.evm.evm_anchor_provider import EvmAnchorProvider
    from app.shared.config import get_settings
    from app.shared.constants import NETWORK_CODE_ETHEREUM_SEPOLIA

    get_settings.cache_clear()
    container = ServiceContainer()
    settings = container.settings
    init_database(settings)

    if not settings.sepolia_ready():
        raise CriticalValidationError(
            "settings.sepolia_ready() retornou False.",
            recommendation="Preencha RPC, chave, contrato e chain_id=11155111.",
        )

    provider = container.providers.get(NETWORK_CODE_ETHEREUM_SEPOLIA)
    if not isinstance(provider, EvmAnchorProvider):
        raise CriticalValidationError(
            f"Provider inesperado: {type(provider).__name__}",
            recommendation="Não use SimulatedAnchorProvider para ethereum_sepolia.",
        )
    if provider.chain_id != SEPOLIA_CHAIN_ID:
        raise CriticalValidationError(
            f"Chain ID interno incorreto: {provider.chain_id}",
            recommendation="Confira BLOCKCHAIN_SEPOLIA_CHAIN_ID.",
        )
    if provider.contract_address.lower() != ctx.contract_address.lower():
        raise CriticalValidationError(
            "Contrato interno diverge do .env.",
            recommendation="Reinicie após corrigir BLOCKCHAIN_SEPOLIA_CONTRACT_ADDRESS.",
        )

    with container.unit_of_work() as uow:
        network = uow.blockchain_networks.get_by_code(NETWORK_CODE_ETHEREUM_SEPOLIA)
        if network is None:
            raise CriticalValidationError(
                "Rede ethereum_sepolia não encontrada no banco.",
                recommendation="Rode init_database / blockchain-init-db.",
            )

    from sqlalchemy import inspect as sa_inspect

    from app.infrastructure.db.connection import create_engine_from_settings

    engine = create_engine_from_settings(settings)
    inspector = sa_inspect(engine)
    cols = [c["name"] for c in inspector.get_columns("blockchain_transaction")]
    has_idem = "idempotency_key" in cols
    if not has_idem:
        raise CriticalValidationError(
            "Coluna idempotency_key ausente.",
            recommendation="Execute scripts/migrate_add_idempotency_key.py.",
        )

    ctx.container = container
    ctx.settings = settings
    details = {
        "settings_class": type(settings).__name__,
        "container_class": type(container).__name__,
        "provider_class": type(provider).__name__,
        "provider_type": provider.provider_type,
        "network_code": NETWORK_CODE_ETHEREUM_SEPOLIA,
        "chain_id": provider.chain_id,
        "contract_address": provider.contract_address,
        "database_url_sanitized": str(settings.database_url).split("://")[0] + "://********",
        "idempotency_key_column": has_idem,
        "sepolia_ready": True,
    }
    for key, value in details.items():
        print(f"{key}: {value}")
    write_evidence(ctx.evidence_dir, "package_validation.json", {"module": details}, TestStatus.PASSED.value)
    return TestResult("Banco", TestStatus.PASSED, details)


def create_sample_evidence_package(container: Any) -> dict[str, Any]:
    """Persist a minimal eligible package using official hash/Merkle services.

    Does not touch Sepolia. Intended for interactive validation when the local
    blockchain DB has no FINAL_ONTOLOGY_PUBLISHED package yet.
    """
    from app.domain.entities import AnchorRequest, EvidenceItem, EvidencePackage, HashRecord
    from app.domain.services.canonical_json_service import to_canonical_json
    from app.domain.services.merkle_service import MerkleLeaf, build_merkle_root
    from app.domain.services.sha256_service import sha256_hex
    from app.domain.value_objects.statuses import (
        AnchorRequestStatus,
        EvidenceItemType,
        EvidencePackageStatus,
        HashSubjectKind,
        RequestScope,
    )
    from app.shared.clock import utcnow
    from app.shared.constants import (
        CANONICALIZATION_METHOD_V1,
        HASH_ALGORITHM_SHA256,
        SCHEMA_VERSION_EVIDENCE_ITEM,
        SCHEMA_VERSION_EVIDENCE_PACKAGE,
    )
    from app.shared.ids import new_id

    now = utcnow()
    request_id = new_id()
    package_id = new_id()
    item_id = new_id()
    source_event_id = f"sepolia-sample-{package_id}"

    item_payload = {
        "core_hashes": {
            "sample_marker": "sepolia_interactive_validation",
            "note": "Pacote de exemplo gerado pelo validar_sepolia_interativo.py",
        },
        "item_id": str(item_id),
        "item_order": 1,
        "item_type": EvidenceItemType.PUBLICATION_RECEIPT.value,
        "schema_version": SCHEMA_VERSION_EVIDENCE_ITEM,
        "source_reference": "sample://sepolia_interactive_validation",
        "period": {
            "period_end": "2026-12-31",
            "period_granularity": "annual",
            "period_start": "2026-01-01",
        },
    }
    item_hash = sha256_hex(item_payload)
    item_canonical = to_canonical_json(item_payload)

    package_type = "ontology_publication"
    package_payload = {
        "evidence_items": [
            {
                "item_hash": item_hash,
                "item_id": str(item_id),
                "item_order": 1,
                "item_type": EvidenceItemType.PUBLICATION_RECEIPT.value,
            }
        ],
        "integrity_context": {
            "canonicalization_method": CANONICALIZATION_METHOD_V1,
            "hash_algorithm": HASH_ALGORITHM_SHA256,
        },
        "package_id": str(package_id),
        "package_type": package_type,
        "package_version": "1.0.0",
        "period_end": "2026-12-31",
        "period_granularity": "annual",
        "period_start": "2026-01-01",
        "schema_version": SCHEMA_VERSION_EVIDENCE_PACKAGE,
        "scope": {
            "farm_id_hash": "0x" + "aa" * 32,
            "management_unit_id_hash": None,
            "project_id_hash": "0x" + "bb" * 32,
        },
    }
    package_hash = sha256_hex(package_payload)
    package_canonical = to_canonical_json(package_payload)
    merkle_root = build_merkle_root(
        [
            MerkleLeaf(
                item_id=str(item_id),
                item_order=1,
                item_hash=item_hash,
            )
        ]
    ).merkle_root
    metadata_hash = sha256_hex(
        {
            "anchor_request_id": str(request_id),
            "event_type": "FINAL_ONTOLOGY_PUBLISHED",
            "source_event_id": source_event_id,
            "sample": True,
        }
    )

    request = AnchorRequest(
        anchor_request_id=request_id,
        source_event_id=source_event_id,
        source_event_type="FINAL_ONTOLOGY_PUBLISHED",
        pipeline_run_id=None,
        calculation_result_set_id=None,
        reporting_period_id=None,
        request_scope=RequestScope.MANUAL.value,
        status=AnchorRequestStatus.READY.value,
        created_at=now,
        updated_at=now,
        error_message=None,
    )
    package = EvidencePackage(
        evidence_package_id=package_id,
        anchor_request_id=request_id,
        package_type=package_type,
        package_version="1.0.0",
        period_start="2026-01-01",
        period_end="2026-12-31",
        period_granularity="annual",
        project_id_hash="0x" + "bb" * 32,
        farm_id_hash="0x" + "aa" * 32,
        management_unit_id_hash=None,
        canonical_payload_json=package_canonical,
        package_hash=package_hash,
        merkle_root=merkle_root,
        metadata_hash=metadata_hash,
        public_summary_enabled=False,
        status=EvidencePackageStatus.READY_TO_ANCHOR.value,
        created_at=now,
        updated_at=now,
    )
    item = EvidenceItem(
        evidence_item_id=item_id,
        evidence_package_id=package_id,
        item_order=1,
        item_type=EvidenceItemType.PUBLICATION_RECEIPT.value,
        source_table="sample_sepolia_validation",
        source_record_id=None,
        source_event_id=source_event_id,
        source_hash_value=item_hash,
        canonical_payload_json=item_canonical,
        item_hash=item_hash,
        created_at=now,
    )
    hash_record = HashRecord(
        hash_record_id=new_id(),
        subject_kind=HashSubjectKind.EVIDENCE_PACKAGE.value,
        subject_id=package_id,
        hash_algorithm=HASH_ALGORITHM_SHA256,
        canonicalization_method=CANONICALIZATION_METHOD_V1,
        hash_value=package_hash,
        payload_ref=package_canonical,
        created_at=now,
    )

    with container.unit_of_work() as uow:
        uow.anchor_requests.add(request)
        uow.evidence_packages.add(package)
        uow.flush()
        uow.evidence_items.add(item)
        uow.hash_records.add(hash_record)

    return {
        "evidence_package_id": str(package_id),
        "anchor_request_id": str(request_id),
        "status": package.status,
        "package_hash": package_hash,
        "merkle_root": merkle_root,
        "event_type": "FINAL_ONTOLOGY_PUBLISHED",
        "period_start": package.period_start,
        "period_end": package.period_end,
        "sample": True,
    }


def _offer_create_sample_package(ctx: ValidationContext) -> UUID:
    print()
    print("Nenhum pacote elegível encontrado no banco local.")
    print("É possível criar um PACOTE DE EXEMPLO (somente SQLite local).")
    print("Isso NÃO envia transação para a Sepolia.")
    print("O pacote usará evento FINAL_ONTOLOGY_PUBLISHED e hashes oficiais.")
    print()
    if ctx.args.create_sample_package:
        print("Flag --create-sample-package detectada.")
    aguardar_enter(
        "Pressione ENTER para criar o pacote de exemplo ou digite qualquer coisa para cancelar: "
    )
    created = create_sample_evidence_package(ctx.container)
    print("Pacote de exemplo criado:")
    for key, value in created.items():
        print(f"  {key}: {value}")
    write_evidence(
        ctx.evidence_dir,
        "package_validation.json",
        {"sample_created": created},
        TestStatus.PASSED.value,
    )
    from app.shared.ids import ensure_uuid

    return ensure_uuid(created["evidence_package_id"])


def test_10_package(ctx: ValidationContext) -> TestResult:
    from app.shared.ids import ensure_uuid

    selected: UUID | None = None
    sample_created = False
    if ctx.args.package_id:
        try:
            selected = ensure_uuid(ctx.args.package_id)
        except Exception as exc:
            raise CriticalValidationError(
                f"package-id inválido: {ctx.args.package_id}",
                recommendation="Informe um UUID válido.",
            ) from exc
    else:
        candidates = list_eligible_packages(ctx.container, limit=20)
        if not candidates:
            selected = _offer_create_sample_package(ctx)
            sample_created = True
        else:
            print("Pacotes candidatos (máx. 20):")
            for idx, item in enumerate(candidates, start=1):
                print(f"\n[{idx}]")
                for key in (
                    "evidence_package_id",
                    "status",
                    "package_hash",
                    "merkle_root",
                    "event_type",
                    "period_start",
                    "period_end",
                ):
                    print(f"  {key}: {item.get(key)}")
            print()
            print(
                "Digite o UUID de um candidato, ou pressione ENTER para criar "
                "um pacote de exemplo local (não ancora na Sepolia ainda)."
            )
            raw = input("UUID do pacote (ENTER = criar exemplo): ").strip()
            if not raw:
                selected = _offer_create_sample_package(ctx)
                sample_created = True
            else:
                try:
                    selected = ensure_uuid(raw)
                except Exception as exc:
                    raise CriticalValidationError(
                        f"UUID inválido: {raw}",
                        recommendation="Confira o formato do evidence_package_id.",
                    ) from exc

    assert selected is not None
    with ctx.container.unit_of_work() as uow:
        package = uow.evidence_packages.get(selected)
        if package is None:
            raise CriticalValidationError(
                f"Pacote inexistente: {selected}",
                recommendation="Crie o pacote via pipeline/CLI ou use o pacote de exemplo.",
            )
        request = uow.anchor_requests.get(package.anchor_request_id)
        if request is None:
            raise CriticalValidationError(
                "Anchor request vinculado não encontrado.",
                recommendation="Verifique a integridade do banco blockchain_service.db.",
            )
        ctx.package = package
        ctx.anchor_request = request
        ctx.package_id = package.evidence_package_id
        ctx.package_hash = package.package_hash or ""
        ctx.merkle_root = package.merkle_root or ""
        ctx.source_event_type = request.source_event_type

    if not ctx.package_hash or not ctx.merkle_root:
        raise CriticalValidationError(
            "Pacote sem package_hash ou merkle_root.",
            recommendation="Construa o pacote com hashes antes de ancorar.",
        )
    if not is_valid_hash_32(ctx.package_hash) or not is_valid_hash_32(ctx.merkle_root):
        raise CriticalValidationError(
            "Hashes do pacote não possuem 32 bytes.",
            recommendation="Recalcule o pacote com o serviço oficial de hash.",
        )

    details = {
        "evidence_package_id": str(ctx.package_id),
        "status": ctx.package.status,
        "package_hash": ctx.package_hash,
        "merkle_root": ctx.merkle_root,
        "event_type": ctx.source_event_type,
        "period_start": ctx.package.period_start,
        "period_end": ctx.package.period_end,
        "sample_created": sample_created,
    }
    for key, value in details.items():
        print(f"{key}: {value}")
    write_evidence(ctx.evidence_dir, "package_validation.json", details, TestStatus.PASSED.value)
    return TestResult("Pacote", TestStatus.PASSED, details)


def test_11_gate(ctx: ValidationContext) -> TestResult:
    from app.domain.services.final_publication_gate import is_final_publication_event
    from app.shared.constants import FINAL_PUBLICATION_EVENT_TYPES

    event = ctx.source_event_type
    released = is_final_publication_event(event)
    print(f"Evento de origem: {event}")
    print(f"Evento considerado final: {event in FINAL_PUBLICATION_EVENT_TYPES}")
    print(f"Gate liberado: {released}")
    if event == "CALCULATION_APPROVED" or not released:
        raise CriticalValidationError(
            f"Gate de publicação final negado para evento {event!r}.",
            recommendation=(
                "Ancore somente após FINAL_ONTOLOGY_PUBLISHED "
                f"(ou aliases: {sorted(FINAL_PUBLICATION_EVENT_TYPES)})."
            ),
        )
    details = {
        "Evento de origem": event,
        "Evento considerado final": True,
        "Gate liberado": True,
        "aliases": sorted(FINAL_PUBLICATION_EVENT_TYPES),
    }
    return TestResult("Gate final", TestStatus.PASSED, details)


def test_12_offchain(ctx: ValidationContext) -> TestResult:
    from app.application.dto.commands import VerifyEvidencePackageCommand
    from app.application.use_cases.verify_evidence_package import VerifyEvidencePackageUseCase

    with ctx.container.unit_of_work() as uow:
        result = VerifyEvidencePackageUseCase(uow).execute(
            VerifyEvidencePackageCommand(evidence_package_id=ctx.package_id)
        )
    details = {
        "is_valid": result.is_valid,
        "details": result.details,
    }
    items = result.details.get("items") or []
    items_ok = all(bool(item.get("is_valid")) for item in items) if items else True
    print(f"item_hash valid: {items_ok}")
    print(f"package_hash valid: {result.details.get('package_hash_valid')}")
    print(f"merkle_root valid: {result.details.get('merkle_root_valid')}")
    print(f"full valid: {result.is_valid}")
    print(f"detalhes: {safe_serialize(result.details)}")
    print(f"is_valid: {result.is_valid}")
    if not result.is_valid:
        raise CriticalValidationError(
            "Pacote off-chain inválido.",
            recommendation="Não ancore pacotes com hashes inconsistentes.",
        )
    return TestResult("Verificação off-chain", TestStatus.PASSED, details)


def test_13_derived(ctx: ValidationContext) -> TestResult:
    from app.domain.services.idempotency_service import build_idempotency_key
    from app.infrastructure.anchoring.evm.evidence_key import (
        evidence_key_hex,
        evidence_package_id_to_key,
    )
    from app.infrastructure.anchoring.evm.hash_conversion import hex_hash_to_bytes32

    evidence_key = evidence_key_hex(ctx.package_id)
    idem = build_idempotency_key(NETWORK_CODE, ctx.package_hash)
    ek_bytes = evidence_package_id_to_key(ctx.package_id)
    ph_bytes = hex_hash_to_bytes32(ctx.package_hash)
    mr_bytes = hex_hash_to_bytes32(ctx.merkle_root)

    ctx.evidence_key = evidence_key
    ctx.idempotency_key = idem

    details = {
        "evidence_package_id": str(ctx.package_id),
        "evidence_key": evidence_key,
        "package_hash": ctx.package_hash,
        "merkle_root": ctx.merkle_root,
        "idempotency_key": idem,
        "network_code": NETWORK_CODE,
        "evidence_key_bytes": len(ek_bytes),
        "package_hash_bytes": len(ph_bytes),
        "merkle_root_bytes": len(mr_bytes),
    }
    for key, value in details.items():
        print(f"{key}: {value}")
    if len(ek_bytes) != 32 or len(ph_bytes) != 32 or len(mr_bytes) != 32:
        raise CriticalValidationError(
            "Tamanhos de bytes32 inconsistentes.",
            recommendation="Verifique evidence_key e hashes oficiais.",
        )
    return TestResult("Cálculos derivados", TestStatus.PASSED, details)


def _independent_web3_query(ctx: ValidationContext) -> dict[str, Any]:
    from app.infrastructure.anchoring.evm.evidence_key import evidence_package_id_to_key
    from app.infrastructure.anchoring.evm.hash_conversion import bytes32_to_hex

    key = evidence_package_id_to_key(ctx.package_id)
    exists = bool(ctx.contract.functions.evidenceExists(key).call())
    package_hash, merkle_root, anchored_at, submitter, exists2 = ctx.contract.functions.getEvidence(
        key
    ).call()
    return {
        "exists": bool(exists and exists2),
        "package_hash": bytes32_to_hex(bytes(package_hash)) if exists2 else None,
        "merkle_root": bytes32_to_hex(bytes(merkle_root)) if exists2 else None,
        "anchored_at": int(anchored_at) if exists2 else None,
        "submitter": submitter if exists2 else None,
        "evidence_key": ctx.evidence_key,
    }


def test_14_pre_query(ctx: ValidationContext) -> TestResult:
    from app.application.dto.commands import QueryAnchoredEvidenceCommand
    from app.application.use_cases.query_anchored_evidence import QueryAnchoredEvidenceUseCase

    with ctx.container.unit_of_work() as uow:
        result = QueryAnchoredEvidenceUseCase(uow, ctx.container.providers).execute(
            QueryAnchoredEvidenceCommand(
                evidence_package_id=ctx.package_id,
                network_code=NETWORK_CODE,
            )
        )
    indep = _independent_web3_query(ctx)
    ctx.pre_query_found = bool(result.found)
    details = {
        "found": result.found,
        "evidence_key": result.evidence_key,
        "package_hash on-chain": result.package_hash,
        "merkle_root on-chain": result.merkle_root,
        "anchored_at": result.anchored_at,
        "submitter": result.submitter,
        "independent_web3": indep,
    }
    for key, value in details.items():
        if key != "independent_web3":
            print(f"{key}: {value}")
    print(f"Consulta independente Web3.py exists: {indep.get('exists')}")
    if result.found:
        print(
            "A evidência já existe. O próximo teste deverá validar o reaproveitamento "
            "idempotente e não enviar uma nova transação."
        )
    else:
        print(
            "A evidência ainda não está ancorada. O próximo teste enviará uma transação real."
        )
    write_evidence(ctx.evidence_dir, "pre_anchor_query.json", details, TestStatus.PASSED.value)
    return TestResult("Consulta prévia", TestStatus.PASSED, details)


def _confirm_real_transaction(ctx: ValidationContext) -> None:
    print()
    print("=" * 60)
    print("CONFIRMAÇÃO DE TRANSAÇÃO REAL")
    print("=" * 60)
    print()
    print("Este teste enviará uma transação real para a Ethereum Sepolia.")
    print("A operação consumirá uma pequena quantidade de SepoliaETH.")
    print("A transação ficará registrada publicamente e poderá ser")
    print("consultada por outras pessoas no explorador da rede.")
    print()
    print(f"Contrato: {ctx.contract_address}")
    print(f"Carteira: {ctx.wallet_address}")
    print(f"Pacote: {ctx.package_id}")
    print(f"Package Hash: {ctx.package_hash}")
    print(f"Merkle Root: {ctx.merkle_root}")
    from web3 import Web3

    saldo = float(Web3.from_wei(ctx.balance_wei, "ether"))
    print(f"Saldo atual: {saldo} SepoliaETH")
    print("Rede: Ethereum Sepolia")
    print(f"Chain ID: {SEPOLIA_CHAIN_ID}")
    print()
    aguardar_enter(
        "Pressione ENTER para confirmar o envio ou digite qualquer coisa para cancelar: "
    )


def _anchor_result_to_dict(result: Any, ctx: ValidationContext) -> dict[str, Any]:
    payload = dict(getattr(result, "provider_response", None) or {})
    return {
        "evidence_package_id": str(result.evidence_package_id),
        "network_code": result.network_code,
        "chain_id": result.chain_id,
        "contract_address": result.contract_address or ctx.contract_address,
        "evidence_key": result.evidence_key or ctx.evidence_key,
        "package_hash": result.package_hash,
        "merkle_root": result.merkle_root,
        "transaction_hash": result.transaction_hash,
        "block_number": result.block_number,
        "anchoring_status": result.anchoring_status,
        "receipt_status": result.receipt_status,
        "gas_used": result.gas_used,
        "effective_gas_price": result.effective_gas_price,
        "from_address": payload.get("from_address") or ctx.wallet_address,
        "anchored_at": payload.get("onchain_anchored_at") or payload.get("anchored_at"),
        "confirmations": payload.get("confirmations", ctx.confirmations),
        "explorer_url": result.explorer_url,
        "idempotent_reuse": result.idempotent_reuse,
        "anchoring_mode": result.anchoring_mode,
    }


def test_15_anchoring(ctx: ValidationContext) -> TestResult:
    if ctx.query_only:
        print("Modo --query-only: ancoragem ignorada.")
        return TestResult("Ancoragem/idempotência", TestStatus.SKIPPED, {"query_only": True})

    # Resume path: recover existing transaction without re-sending
    if ctx.resume_mode and ctx.args.resume_transaction:
        tx_hash = ctx.args.resume_transaction
        print(f"Modo retomada: transaction_hash={tx_hash}")
        print("Nenhuma nova transação será enviada.")
        try:
            receipt = ctx.w3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=ctx.receipt_timeout
            )
        except Exception as exc:
            print("[FALHOU — ANCORAGEM REAL NÃO CONCLUÍDA]")
            raise CriticalValidationError(
                f"Falha ao recuperar recibo: {type(exc).__name__}: {exc}",
                recommendation=(
                    "Aguarde confirmação na Sepolia e execute novamente com "
                    "--resume-transaction. Não reenvie a mesma evidência."
                ),
            ) from exc
        status = int(receipt.get("status", 0))
        ctx.transaction_hash = tx_hash if tx_hash.startswith("0x") else "0x" + tx_hash
        ctx.block_number = int(receipt["blockNumber"])
        ctx.idempotent_reuse = True
        ctx.anchoring_result = {
            "evidence_package_id": str(ctx.package_id),
            "network_code": NETWORK_CODE,
            "chain_id": SEPOLIA_CHAIN_ID,
            "contract_address": ctx.contract_address,
            "evidence_key": ctx.evidence_key,
            "package_hash": ctx.package_hash,
            "merkle_root": ctx.merkle_root,
            "transaction_hash": ctx.transaction_hash,
            "block_number": ctx.block_number,
            "anchoring_status": "confirmed" if status == 1 else "reverted",
            "receipt_status": status,
            "gas_used": int(receipt.get("gasUsed", 0)),
            "effective_gas_price": int(receipt.get("effectiveGasPrice") or 0),
            "from_address": receipt.get("from"),
            "confirmations": ctx.confirmations,
            "explorer_url": explorer_tx_url(ctx.explorer_base, ctx.transaction_hash),
            "idempotent_reuse": True,
            "resume_mode": True,
        }
        for key, value in ctx.anchoring_result.items():
            print(f"{key}: {value}")
        if status != 1:
            print("[FALHOU — ANCORAGEM REAL NÃO CONCLUÍDA]")
            raise CriticalValidationError(
                "Transação retomada com status != 1.",
                recommendation="Consulte o explorador; não reenvie automaticamente.",
            )
        write_evidence(
            ctx.evidence_dir, "anchoring_result.json", ctx.anchoring_result, TestStatus.PASSED.value
        )
        return TestResult("Ancoragem/idempotência", TestStatus.PASSED, ctx.anchoring_result)

    # If already on-chain, still call official UC (expect idempotent reuse or duplicate handling)
    if not ctx.pre_query_found:
        print()
        print("ATENÇÃO: ESTE TESTE PODE ENVIAR UMA TRANSAÇÃO REAL PARA A ETHEREUM SEPOLIA")
        print("E CONSUMIR SEPOLIAETH.")
        print()
        aguardar_enter("Pressione ENTER para continuar com a confirmação detalhada: ")
        _confirm_real_transaction(ctx)
    else:
        print("Evidência já on-chain — chamando caso de uso oficial (espera-se idempotência).")
        aguardar_enter(
            "Pressione ENTER para executar a ancoragem oficial (sem nova tx se idempotente): "
        )

    from app.application.dto.commands import AnchorEvidencePackageCommand
    from app.application.use_cases.anchor_evidence_package import AnchorEvidencePackageUseCase

    try:
        with ctx.container.unit_of_work() as uow:
            result = AnchorEvidencePackageUseCase(uow, ctx.container.providers).execute(
                AnchorEvidencePackageCommand(
                    evidence_package_id=ctx.package_id,
                    network_code=NETWORK_CODE,
                )
            )
    except Exception as exc:
        print("[FALHOU — ANCORAGEM REAL NÃO CONCLUÍDA]")
        onchain_after: dict[str, Any] = {}
        try:
            onchain_after = _independent_web3_query(ctx)
        except Exception as query_exc:
            onchain_after = {"query_error": type(query_exc).__name__}
        exists_now = bool(onchain_after.get("exists"))
        recomendacao = (
            "Não troque para local_simulated. Se houver transaction_hash, "
            "use --resume-transaction. Verifique saldo, owner e gate final."
        )
        if exists_now:
            recomendacao = (
                "A evidência JÁ aparece on-chain (a tx pode ter sido minerada antes "
                "da falha local). Não reenvie. Consulte o explorador da carteira, "
                f"use query-anchor --package-id {ctx.package_id}, ou "
                "validar_sepolia_interativo.py --package-id ... --resume-transaction <TX_HASH>."
            )
        err = {
            "tipo": type(exc).__name__,
            "causa": str(exc)[:500],
            "transacao_enviada_conhecida": exists_now,
            "onchain_apos_falha": onchain_after,
            "diretorio_evidencias": str(ctx.evidence_dir),
            "recomendacao": recomendacao,
        }
        write_evidence(ctx.evidence_dir, "anchoring_result.json", err, TestStatus.FAILED.value)
        print(json.dumps(safe_serialize(err), indent=2, ensure_ascii=False))
        raise CriticalValidationError(
            f"Ancoragem real falhou: {type(exc).__name__}: {exc}",
            recommendation=recomendacao,
        ) from exc

    data = _anchor_result_to_dict(result, ctx)
    ctx.anchoring_result = data
    ctx.transaction_hash = data.get("transaction_hash")
    ctx.block_number = data.get("block_number")
    ctx.idempotent_reuse = bool(data.get("idempotent_reuse"))

    for key, value in data.items():
        print(f"{key}: {value}")

    ok_confirmed = (
        data.get("network_code") == NETWORK_CODE
        and data.get("chain_id") == SEPOLIA_CHAIN_ID
        and (
            (data.get("anchoring_status") == "confirmed" and data.get("receipt_status") == 1)
            or data.get("idempotent_reuse") is True
        )
    )
    if data.get("transaction_hash") and not is_valid_hash_32(str(data["transaction_hash"])):
        ok_confirmed = False
    if data.get("idempotent_reuse") is not True:
        if not data.get("block_number") or int(data.get("block_number") or 0) <= 0:
            ok_confirmed = False

    if not ok_confirmed:
        print("[FALHOU — ANCORAGEM REAL NÃO CONCLUÍDA]")
        write_evidence(ctx.evidence_dir, "anchoring_result.json", data, TestStatus.FAILED.value)
        raise CriticalValidationError(
            "Critérios de sucesso da ancoragem real não atendidos.",
            recommendation="Inspecione o recibo e o explorador; não force nova tx.",
        )

    write_evidence(ctx.evidence_dir, "anchoring_result.json", data, TestStatus.PASSED.value)
    return TestResult("Ancoragem/idempotência", TestStatus.PASSED, data)


def test_16_receipt(ctx: ValidationContext) -> TestResult:
    if ctx.query_only and not ctx.transaction_hash:
        # Try get from pre-query / chain
        if ctx.pre_query_found:
            print("query-only sem transaction_hash local — recibo marcado como IGNORADO.")
            return TestResult("Recibo", TestStatus.SKIPPED, {})
        return TestResult("Recibo", TestStatus.SKIPPED, {"query_only": True})

    tx_hash = ctx.transaction_hash
    if not tx_hash:
        # Try DB
        with ctx.container.unit_of_work() as uow:
            tx = uow.blockchain_transactions.get_latest_for_package(ctx.package_id)
            if tx and tx.transaction_hash:
                tx_hash = tx.transaction_hash
                ctx.transaction_hash = tx_hash
                ctx.block_number = tx.block_number
    if not tx_hash:
        raise CriticalValidationError(
            "transaction_hash ausente para consulta de recibo.",
            recommendation="Execute ancoragem ou --resume-transaction.",
        )

    receipt = ctx.w3.eth.get_transaction_receipt(tx_hash)
    current_block = int(ctx.w3.eth.block_number)
    confs = current_block - int(receipt["blockNumber"]) + 1
    details = {
        "transactionHash": bytes32_hex_from_value(receipt["transactionHash"]),
        "blockNumber": int(receipt["blockNumber"]),
        "blockHash": bytes32_hex_from_value(receipt["blockHash"]),
        "transactionIndex": int(receipt["transactionIndex"]),
        "from": receipt.get("from"),
        "to": receipt.get("to"),
        "status": int(receipt.get("status", 0)),
        "gasUsed": int(receipt["gasUsed"]),
        "effectiveGasPrice": int(receipt.get("effectiveGasPrice") or 0),
        "cumulativeGasUsed": int(receipt.get("cumulativeGasUsed") or 0),
        "logs count": len(receipt.get("logs") or []),
        "confirmations atuais": confs,
        "explorer_url": explorer_tx_url(ctx.explorer_base, tx_hash),
    }
    for key, value in details.items():
        print(f"{key}: {value}")

    if details["status"] != 1:
        raise CriticalValidationError(
            "receipt.status != 1 (transação revertida).",
            recommendation="Consulte o explorador; não reenvie sem diagnóstico.",
        )
    if details["to"] and details["to"].lower() != ctx.contract_address.lower():
        raise CriticalValidationError(
            "Recibo 'to' diverge do contrato.",
            recommendation="Confirme o endereço do contrato no .env.",
        )
    if details["from"] and details["from"].lower() != ctx.wallet_address.lower():
        raise CriticalValidationError(
            "Recibo 'from' diverge da carteira configurada.",
            recommendation="Confirme a chave privada / owner.",
        )

    ctx.receipt = details
    write_evidence(ctx.evidence_dir, "transaction_receipt.json", details, TestStatus.PASSED.value)
    return TestResult("Recibo", TestStatus.PASSED, details)


def test_17_event(ctx: ValidationContext) -> TestResult:
    tx_hash = ctx.transaction_hash
    if not tx_hash:
        with ctx.container.unit_of_work() as uow:
            tx = uow.blockchain_transactions.get_latest_for_package(ctx.package_id)
            if tx and tx.transaction_hash:
                tx_hash = tx.transaction_hash
                ctx.transaction_hash = tx_hash
    if not tx_hash:
        if ctx.query_only:
            return TestResult("Evento", TestStatus.SKIPPED, {"reason": "sem transaction_hash"})
        raise CriticalValidationError(
            "Sem transaction_hash para decodificar evento.",
            recommendation="Use ancoragem ou retomada.",
        )

    receipt = ctx.w3.eth.get_transaction_receipt(tx_hash)
    events = ctx.contract.events.EvidenceAnchored().process_receipt(receipt)
    if not events:
        raise CriticalValidationError(
            "Evento EvidenceAnchored não encontrado nos logs.",
            recommendation="Confirme ABI e que a tx chamou anchorEvidence.",
        )
    args = events[0]["args"]
    event_key = bytes32_hex_from_value(args["evidenceKey"])
    event_ph = bytes32_hex_from_value(args["packageHash"])
    event_mr = bytes32_hex_from_value(args["merkleRoot"])
    submitter = args["submitter"]
    anchored_at = int(args["anchoredAt"])

    matches = {
        "event_evidence_key_match": hex_eq(event_key, ctx.evidence_key),
        "event_package_hash_match": hex_eq(event_ph, ctx.package_hash),
        "event_merkle_root_match": hex_eq(event_mr, ctx.merkle_root),
        "event_submitter_match": submitter.lower() == ctx.wallet_address.lower(),
    }
    details = {
        "evidenceKey": event_key,
        "packageHash": event_ph,
        "merkleRoot": event_mr,
        "submitter": submitter,
        "anchoredAt": anchored_at,
        **matches,
    }
    for key, value in details.items():
        print(f"{key}: {value}")
    if not all(matches.values()):
        raise CriticalValidationError(
            "Campos do evento divergem dos valores locais.",
            recommendation="Compare package_hash/merkle_root locais com o evento.",
        )
    ctx.event_data = details
    write_evidence(ctx.evidence_dir, "contract_event.json", details, TestStatus.PASSED.value)
    return TestResult("Evento", TestStatus.PASSED, details)


def test_18_post_query(ctx: ValidationContext) -> TestResult:
    from app.application.dto.commands import QueryAnchoredEvidenceCommand
    from app.application.use_cases.query_anchored_evidence import QueryAnchoredEvidenceUseCase

    with ctx.container.unit_of_work() as uow:
        result = QueryAnchoredEvidenceUseCase(uow, ctx.container.providers).execute(
            QueryAnchoredEvidenceCommand(
                evidence_package_id=ctx.package_id,
                network_code=NETWORK_CODE,
            )
        )
    indep = _independent_web3_query(ctx)
    uc_found = bool(result.found)
    web3_found = bool(indep.get("exists"))
    equivalent = (
        uc_found == web3_found
        and hex_eq(result.package_hash, indep.get("package_hash"))
        and hex_eq(result.merkle_root, indep.get("merkle_root"))
    )
    print(f"Consulta pelo caso de uso: {'encontrada' if uc_found else 'não encontrada'}")
    print(f"Consulta independente Web3.py: {'encontrada' if web3_found else 'não encontrada'}")
    print(f"Resultados equivalentes: {equivalent}")

    package_hash_match = hex_eq(result.package_hash, ctx.package_hash)
    merkle_root_match = hex_eq(result.merkle_root, ctx.merkle_root)
    submitter_match = bool(result.submitter) and result.submitter.lower() == ctx.wallet_address.lower()

    details = {
        "found": result.found,
        "evidence_key": result.evidence_key,
        "package_hash": result.package_hash,
        "merkle_root": result.merkle_root,
        "anchored_at": result.anchored_at,
        "submitter": result.submitter,
        "network_code": result.network_code,
        "chain_id": result.chain_id,
        "contract_address": result.contract_address,
        "independent_web3": indep,
        "package_hash_match": package_hash_match,
        "merkle_root_match": merkle_root_match,
        "submitter_match": submitter_match,
        "results_equivalent": equivalent,
    }
    for key, value in details.items():
        if key != "independent_web3":
            print(f"{key}: {value}")

    if not (
        result.found
        and indep.get("exists")
        and package_hash_match
        and merkle_root_match
        and submitter_match
        and equivalent
    ):
        raise CriticalValidationError(
            "Consulta pós-ancoragem inválida ou divergente.",
            recommendation="Compare UC vs Web3.py e hashes locais.",
        )
    ctx.post_query = details
    write_evidence(ctx.evidence_dir, "post_anchor_query.json", details, TestStatus.PASSED.value)
    return TestResult("Consulta posterior", TestStatus.PASSED, details)


def test_19_verify(ctx: ValidationContext) -> TestResult:
    from app.application.dto.commands import VerifyAnchoredEvidenceCommand
    from app.application.use_cases.verify_anchored_evidence import VerifyAnchoredEvidenceUseCase

    with ctx.container.unit_of_work() as uow:
        result = VerifyAnchoredEvidenceUseCase(uow, ctx.container.providers).execute(
            VerifyAnchoredEvidenceCommand(
                evidence_package_id=ctx.package_id,
                network_code=NETWORK_CODE,
            )
        )
    details = {
        "offchain_valid": result.offchain_valid,
        "onchain_found": result.onchain_found,
        "package_hash_match": result.package_hash_match,
        "merkle_root_match": result.merkle_root_match,
        "network_match": result.network_match,
        "contract_match": result.contract_match,
        "overall_valid": result.overall_valid,
        "details": safe_serialize(result.details),
    }
    for key, value in details.items():
        print(f"{key}: {value}")
    if not result.overall_valid:
        raise CriticalValidationError(
            "Verificação completa retornou overall_valid=False.",
            recommendation="Investigue divergências off-chain/on-chain.",
        )
    ctx.verify_result = details
    write_evidence(
        ctx.evidence_dir, "integrity_verification.json", details, TestStatus.PASSED.value
    )
    return TestResult("Verificação on-chain", TestStatus.PASSED, details)


def test_20_idempotency(ctx: ValidationContext) -> TestResult:
    if ctx.query_only:
        return TestResult("Idempotência", TestStatus.SKIPPED, {"query_only": True})

    from app.application.dto.commands import AnchorEvidencePackageCommand
    from app.application.use_cases.anchor_evidence_package import AnchorEvidencePackageUseCase

    tx_before = ctx.transaction_hash
    block_before = ctx.block_number
    nonce_before = int(ctx.w3.eth.get_transaction_count(ctx.wallet_address, "pending"))
    count_before = count_transactions_for_package(ctx.container, ctx.package_id)
    print(f"transaction_hash anterior: {tx_before}")
    print(f"block_number anterior: {block_before}")
    print(f"nonce pending anterior: {nonce_before}")
    print(f"quantidade de transações persistidas: {count_before}")

    # Resume without DB row: calling submit would hit DuplicateEvidenceError after send path.
    # Prefer official UC when possible; if duplicate on-chain, validate without new tx.
    data: dict[str, Any]
    try:
        with ctx.container.unit_of_work() as uow:
            result = AnchorEvidencePackageUseCase(uow, ctx.container.providers).execute(
                AnchorEvidencePackageCommand(
                    evidence_package_id=ctx.package_id,
                    network_code=NETWORK_CODE,
                )
            )
        data = _anchor_result_to_dict(result, ctx)
    except Exception as exc:
        nonce_mid = int(ctx.w3.eth.get_transaction_count(ctx.wallet_address, "pending"))
        indep = _independent_web3_query(ctx)
        if indep.get("exists") and nonce_mid == nonce_before:
            print(
                f"Caso de uso recusou reenvio ({type(exc).__name__}); "
                "evidência permanece on-chain e nonce não aumentou."
            )
            data = {
                "evidence_package_id": str(ctx.package_id),
                "network_code": NETWORK_CODE,
                "chain_id": SEPOLIA_CHAIN_ID,
                "transaction_hash": tx_before,
                "block_number": block_before,
                "idempotent_reuse": True,
                "provider_error": type(exc).__name__,
                "onchain_exists": True,
            }
        else:
            raise CriticalValidationError(
                f"Idempotência falhou: {type(exc).__name__}: {exc}",
                recommendation="Não reenvie; consulte o explorador e o banco local.",
            ) from exc

    nonce_after = int(ctx.w3.eth.get_transaction_count(ctx.wallet_address, "pending"))
    count_after = count_transactions_for_package(ctx.container, ctx.package_id)

    checks = {
        "idempotent_reuse": bool(data.get("idempotent_reuse")),
        "transaction_hash_unchanged": hex_eq(str(data.get("transaction_hash")), str(tx_before)),
        "block_number_unchanged": data.get("block_number") == block_before,
        "nonce_unchanged": nonce_after == nonce_before,
        "no_new_persisted_tx": count_after <= count_before + 0,
    }
    # Allow count_after == count_before (ideal) — never more after idempotent path that reused
    if count_after > count_before:
        checks["no_new_persisted_tx"] = False

    print(f"transaction_hash depois: {data.get('transaction_hash')}")
    print(f"block_number depois: {data.get('block_number')}")
    print(f"nonce pending depois: {nonce_after}")
    print(f"quantidade de transações persistidas depois: {count_after}")
    for key, value in checks.items():
        print(f"{key}: {value}")

    details = {
        "before": {
            "tx": tx_before,
            "block": block_before,
            "nonce": nonce_before,
            "count": count_before,
        },
        "after": data,
        "checks": checks,
    }
    if not all(checks.values()):
        write_evidence(
            ctx.evidence_dir, "idempotency_validation.json", details, TestStatus.FAILED.value
        )
        raise CriticalValidationError(
            "Idempotência não confirmada.",
            recommendation="Verifique se uma segunda tx foi enviada no explorador.",
        )
    write_evidence(
        ctx.evidence_dir, "idempotency_validation.json", details, TestStatus.PASSED.value
    )
    return TestResult("Idempotência", TestStatus.PASSED, details)


def test_21_tampering(ctx: ValidationContext) -> TestResult:
    from app.domain.services.canonical_json_service import parse_canonical_json, to_canonical_json
    from app.domain.services.sha256_service import sha256_hex

    original_json = ctx.package.canonical_payload_json or "{}"
    payload_original = parse_canonical_json(original_json)
    payload_adulterado = copy.deepcopy(payload_original)

    # Choose a non-sensitive field to alter
    field_name = "campo_teste_validacao_sepolia"
    original_value = payload_adulterado.get(field_name)
    payload_adulterado[field_name] = "VALOR_ADULTERADO"

    hash_original = sha256_hex(payload_original)
    hash_adulterado = sha256_hex(payload_adulterado)
    hash_onchain = ctx.post_query.get("package_hash") or ctx.package_hash

    # Ensure stored package payload unchanged
    with ctx.container.unit_of_work() as uow:
        fresh = uow.evidence_packages.get(ctx.package_id)
        preserved = (fresh.canonical_payload_json or "") == original_json

    # Official stored hash must match on-chain; recomputed original must match stored hash
    original_match = hex_eq(ctx.package_hash, hash_onchain) and hex_eq(
        hash_original, ctx.package_hash
    )
    tampered_match = hex_eq(hash_adulterado, hash_onchain)
    tampered_integrity = tampered_match

    details = {
        "campo alterado": field_name,
        "valor original resumido": str(original_value)[:80] if original_value is not None else "(ausente)",
        "valor adulterado": "VALOR_ADULTERADO",
        "Payload original preservado": preserved,
        "Hash original": hash_original,
        "Hash adulterado": hash_adulterado,
        "Hash on-chain": hash_onchain,
        "Original corresponde ao on-chain": original_match,
        "Adulterado corresponde ao on-chain": tampered_match,
        "Integridade original": original_match,
        "Integridade adulterada": tampered_integrity,
        "original_match": original_match,
        "tampered_match": tampered_match,
        "tampered_integrity": tampered_integrity,
        "canonical_adulterado_len": len(to_canonical_json(payload_adulterado)),
    }
    for key, value in details.items():
        print(f"{key}: {value}")

    if not (original_match and not tampered_match and not tampered_integrity and preserved):
        write_evidence(
            ctx.evidence_dir, "tampering_validation.json", details, TestStatus.FAILED.value
        )
        raise CriticalValidationError(
            "Teste de adulteração não produziu o resultado esperado.",
            recommendation="Confirme que o hash on-chain bate com o pacote oficial.",
        )
    write_evidence(
        ctx.evidence_dir, "tampering_validation.json", details, TestStatus.PASSED.value
    )
    return TestResult("Adulteração", TestStatus.PASSED, details)


def test_22_revalidate(ctx: ValidationContext) -> TestResult:
    from app.application.dto.commands import VerifyAnchoredEvidenceCommand
    from app.application.use_cases.verify_anchored_evidence import VerifyAnchoredEvidenceUseCase

    with ctx.container.unit_of_work() as uow:
        result = VerifyAnchoredEvidenceUseCase(uow, ctx.container.providers).execute(
            VerifyAnchoredEvidenceCommand(
                evidence_package_id=ctx.package_id,
                network_code=NETWORK_CODE,
            )
        )
    details = {
        "overall_valid": result.overall_valid,
        "offchain_valid": result.offchain_valid,
        "onchain_found": result.onchain_found,
        "package_hash_match": result.package_hash_match,
        "merkle_root_match": result.merkle_root_match,
    }
    for key, value in details.items():
        print(f"{key}: {value}")
    if not result.overall_valid:
        raise CriticalValidationError(
            "Revalidação do original falhou após adulteração em memória.",
            recommendation="Garanta que o teste de adulteração não persistiu alterações.",
        )
    write_evidence(
        ctx.evidence_dir, "original_revalidation.json", details, TestStatus.PASSED.value
    )
    return TestResult("Revalidação original", TestStatus.PASSED, details)


# ---------------------------------------------------------------------------
# Summary / VALIDACAO_EXECUTADA
# ---------------------------------------------------------------------------


SUMMARY_ROWS = [
    ("Raiz do módulo", "Raiz do módulo"),
    ("Arquivo .env", "Arquivo .env"),
    ("Configuração", "Configuração"),
    ("RPC Sepolia", "RPC Sepolia"),
    ("Carteira", "Carteira"),
    ("Saldo", "Saldo"),
    ("Contrato", "Contrato"),
    ("ABI", "ABI"),
    ("Owner", "Owner"),
    ("Banco", "Banco"),
    ("Pacote", "Pacote"),
    ("Gate final", "Gate final"),
    ("Verificação off-chain", "Verificação off-chain"),
    ("Consulta prévia", "Consulta prévia"),
    ("Ancoragem/idempotência", "Ancoragem/idempotência"),
    ("Recibo", "Recibo"),
    ("Evento", "Evento"),
    ("Consulta posterior", "Consulta posterior"),
    ("Verificação on-chain", "Verificação on-chain"),
    ("Idempotência", "Idempotência"),
    ("Adulteração", "Adulteração"),
    ("Revalidação original", "Revalidação original"),
]


def _status_for_name(results: list[TestResult], name: str) -> str:
    for item in results:
        if item.name == name:
            return item.status.value
    # Carteira/Saldo share test_05
    if name == "Saldo":
        for item in results:
            if item.name in ("Carteira", "Saldo"):
                if item.status == TestStatus.WARNING:
                    return TestStatus.WARNING.value
                return item.status.value
        return "—"
    if name == "Carteira":
        for item in results:
            if item.name in ("Carteira", "Saldo"):
                return TestStatus.PASSED.value if item.status != TestStatus.FAILED else item.status.value
        return "—"
    return "—"


def print_final_summary(ctx: ValidationContext) -> None:
    print()
    print("=" * 60)
    print("RESUMO FINAL DA VALIDAÇÃO ETHEREUM SEPOLIA")
    print("=" * 60)
    print()
    print(f"{'Teste':<44} {'Status'}")
    print("-" * 60)
    for label, name in SUMMARY_ROWS:
        print(f"{label:<44} {_status_for_name(ctx.results, name)}")

    passed = sum(1 for r in ctx.results if r.status == TestStatus.PASSED)
    warnings = sum(1 for r in ctx.results if r.status == TestStatus.WARNING)
    failed = sum(1 for r in ctx.results if r.status == TestStatus.FAILED)
    skipped = sum(1 for r in ctx.results if r.status == TestStatus.SKIPPED)

    overall_ok = failed == 0 and any(
        r.name in ("Ancoragem/idempotência", "Consulta posterior", "Verificação on-chain")
        and r.status == TestStatus.PASSED
        for r in ctx.results
    )
    if ctx.query_only:
        overall_ok = failed == 0

    from web3 import Web3

    saldo_final = None
    if ctx.w3 and ctx.wallet_address:
        try:
            saldo_final = float(Web3.from_wei(ctx.w3.eth.get_balance(ctx.wallet_address), "ether"))
        except Exception:
            saldo_final = None

    print()
    print(f"Chain ID: {ctx.chain_id}")
    print(f"Carteira pública: {ctx.wallet_address}")
    print(f"Saldo final: {saldo_final}")
    print(f"Contrato: {ctx.contract_address}")
    print(f"Package ID: {ctx.package_id}")
    print(f"Evidence Key: {ctx.evidence_key}")
    print(f"Package Hash: {ctx.package_hash}")
    print(f"Merkle Root: {ctx.merkle_root}")
    print(f"Transaction Hash: {ctx.transaction_hash}")
    print(f"Block Number: {ctx.block_number}")
    explorer = (
        explorer_tx_url(ctx.explorer_base, ctx.transaction_hash)
        if ctx.transaction_hash
        else None
    )
    print(f"Explorer URL: {explorer}")
    print(f"Diretório das evidências: {ctx.evidence_dir}")
    print(f"Quantidade de testes aprovados: {passed}")
    print(f"Quantidade de avisos: {warnings}")
    print(f"Quantidade de falhas: {failed}")
    print(f"Quantidade de ignorados: {skipped}")
    print(f"Resultado geral: {'VALIDAÇÃO CONCLUÍDA COM SUCESSO' if overall_ok else 'VALIDAÇÃO NÃO CONCLUÍDA'}")

    if ctx.transaction_hash:
        print(explorer_tx_url(ctx.explorer_base, ctx.transaction_hash))
    if ctx.contract_address:
        print(explorer_address_url(ctx.explorer_base, ctx.contract_address))


def write_public_links(ctx: ValidationContext) -> None:
    links = {
        "tx": explorer_tx_url(ctx.explorer_base, ctx.transaction_hash) if ctx.transaction_hash else None,
        "contract": explorer_address_url(ctx.explorer_base, ctx.contract_address)
        if ctx.contract_address
        else None,
    }
    write_evidence(ctx.evidence_dir, "public_links.json", links, TestStatus.PASSED.value)


def write_summary_json(ctx: ValidationContext, overall_ok: bool) -> None:
    payload = {
        "overall": "SUCCESS" if overall_ok else "FAILURE",
        "results": [
            {"name": r.name, "status": r.status.value, "message": r.message} for r in ctx.results
        ],
        "chain_id": ctx.chain_id,
        "wallet": ctx.wallet_address,
        "contract": ctx.contract_address,
        "package_id": str(ctx.package_id) if ctx.package_id else None,
        "evidence_key": ctx.evidence_key,
        "package_hash": ctx.package_hash,
        "merkle_root": ctx.merkle_root,
        "transaction_hash": ctx.transaction_hash,
        "block_number": ctx.block_number,
    }
    write_evidence(
        ctx.evidence_dir,
        "summary.json",
        payload,
        TestStatus.PASSED.value if overall_ok else TestStatus.FAILED.value,
    )


def write_validacao_executada(ctx: ValidationContext) -> None:
    lines = [
        "# Validação Sepolia executada",
        "",
        f"- Data/hora (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Rede: Ethereum Sepolia (`{NETWORK_CODE}`)",
        f"- Chain ID: {ctx.chain_id}",
        f"- Carteira pública: `{ctx.wallet_address}`",
        f"- Contrato: `{ctx.contract_address}`",
        f"- Package ID: `{ctx.package_id}`",
        f"- Evidence Key: `{ctx.evidence_key}`",
        f"- Package Hash: `{ctx.package_hash}`",
        f"- Merkle Root: `{ctx.merkle_root}`",
        f"- Transaction Hash: `{ctx.transaction_hash}`",
        f"- Block Number: `{ctx.block_number}`",
        f"- Gas utilizado: `{ctx.anchoring_result.get('gas_used')}`",
        f"- Explorer URL: {explorer_tx_url(ctx.explorer_base, ctx.transaction_hash) if ctx.transaction_hash else 'n/a'}",
        f"- Consulta: found={ctx.post_query.get('found')}",
        f"- Verificação: overall_valid={ctx.verify_result.get('overall_valid')}",
        f"- Idempotência: {ctx.idempotent_reuse}",
        f"- Adulteração: ver `tampering_validation.json`",
        "",
        "## Arquivos JSON",
        "",
    ]
    for path in sorted(ctx.evidence_dir.glob("*.json")):
        lines.append(f"- `{path.name}`")
    lines.extend(["", "## Conclusão", "", "VALIDAÇÃO CONCLUÍDA COM SUCESSO", ""])
    (ctx.evidence_dir / "VALIDACAO_EXECUTADA.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_test(
    ctx: ValidationContext,
    definition: TestDefinition,
    fn,
    *,
    skip_pauses: bool = False,
) -> TestResult:
    if not skip_pauses:
        pause_before_test(definition)
    try:
        result = fn(ctx)
        print_status(result.status)
        ctx.results.append(result)
        if result.name == "Carteira":
            saldo_status = (
                TestStatus.WARNING
                if result.status == TestStatus.WARNING
                else TestStatus.PASSED
            )
            ctx.results.append(
                TestResult(
                    "Saldo",
                    saldo_status,
                    {"saldo_wei": ctx.balance_wei},
                    message="derivado do teste de carteira",
                )
            )
        if ctx.logger:
            ctx.logger.info("TESTE %s %s: %s", definition.number, definition.name, result.status.value)
        if not skip_pauses:
            pause_after_test()
        return result
    except UserAbortedError:
        raise
    except CriticalValidationError as exc:
        print_status(TestStatus.FAILED)
        print(f"Causa: {exc}")
        if exc.recommendation:
            print(f"Recomendação: {exc.recommendation}")
        if ctx.logger:
            ctx.logger.error("Falha crítica: %s\n%s", exc, traceback.format_exc())
        ctx.results.append(
            TestResult(definition.name, TestStatus.FAILED, {}, message=str(exc))
        )
        write_summary_json(ctx, overall_ok=False)
        raise
    except Exception as exc:
        print_status(TestStatus.FAILED)
        print(f"Erro inesperado: {type(exc).__name__}: {exc}")
        if ctx.logger:
            ctx.logger.error("Erro: %s\n%s", exc, traceback.format_exc())
        ctx.results.append(
            TestResult(definition.name, TestStatus.FAILED, {}, message=str(exc))
        )
        write_summary_json(ctx, overall_ok=False)
        raise CriticalValidationError(
            str(exc),
            recommendation="Consulte execution.log no diretório de evidências.",
        ) from exc


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print("MODO DE EXECUÇÃO: ETHEREUM SEPOLIA REAL")
    print()

    missing = check_dependencies()
    if missing:
        return 2

    try:
        root = detect_project_root()
    except CriticalValidationError as exc:
        print(f"[FALHOU] {exc}")
        if exc.recommendation:
            print(exc.recommendation)
        return 1

    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    evidence_dir = root / "evidence" / "sepolia" / f"interactive_validation_{now_stamp()}"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(evidence_dir)

    ctx = ValidationContext(
        root=root,
        evidence_dir=evidence_dir,
        env_path=root / ".env",
        args=args,
        logger=logger,
        query_only=bool(args.query_only),
        resume_mode=bool(args.resume_transaction),
    )

    tests: list[tuple[TestDefinition, Any]] = [
        (
            TestDefinition(
                1,
                "Localização da raiz",
                "Confirmar que o script está na raiz do módulo blockchain-service.",
                "Verificar pyproject.toml, app/, contracts/, schemas/, scripts/.",
                "Raiz detectada com todos os artefatos obrigatórios.",
            ),
            test_01_root,
        ),
        (
            TestDefinition(
                2,
                "Arquivo .env",
                "Validar existência e leitura do .env sem expor segredos.",
                "Localizar .env e carregar com load_dotenv(override=True).",
                "Arquivo encontrado e legível.",
            ),
            test_02_env,
        ),
        (
            TestDefinition(
                3,
                "Variáveis obrigatórias",
                "Validar presença e formato das configurações Sepolia.",
                "Checar variáveis BLOCKCHAIN_SEPOLIA_* sem imprimir segredos.",
                "RPC, chave, contrato e chain_id=11155111 válidos.",
            ),
            test_03_vars,
        ),
        (
            TestDefinition(
                4,
                "Conexão RPC",
                "Conectar ao RPC Sepolia e validar chain ID.",
                "Web3.HTTPProvider + is_connected + eth.chain_id.",
                "Conectado: True; Chain ID: 11155111.",
            ),
            test_04_rpc,
        ),
        (
            TestDefinition(
                5,
                "Carteira e saldo",
                "Derivar endereço da chave e consultar saldo/nonce.",
                "Account.from_key + get_balance + get_transaction_count.",
                "Endereço público e saldo > 0 (aviso se zero).",
            ),
            test_05_wallet,
        ),
        (
            TestDefinition(
                6,
                "Contrato e bytecode",
                "Validar que o endereço do contrato possui bytecode.",
                "Web3.to_checksum_address + eth.get_code.",
                "Bytecode encontrado: True; tamanho > 0.",
            ),
            test_06_contract,
        ),
        (
            TestDefinition(
                7,
                "ABI",
                "Carregar e validar a ABI do CarbonEvidenceRegistry.",
                "Ler CarbonEvidenceRegistry.abi.json e checar funções/eventos.",
                "ABI com owner, anchorEvidence, getEvidence, evidenceExists, EvidenceAnchored.",
            ),
            test_07_abi,
        ),
        (
            TestDefinition(
                8,
                "Proprietário e autorização",
                "Confirmar que a carteira é owner do contrato.",
                "Chamada owner() e comparação com endereço derivado.",
                "Carteira autorizada: True.",
            ),
            test_08_owner,
        ),
        (
            TestDefinition(
                9,
                "Configuração interna do módulo",
                "Instanciar ServiceContainer e validar provider/rede/banco.",
                "ServiceContainer + ProvidersRegistry + schema idempotency_key.",
                "Provider EVM Sepolia e banco utilizável.",
            ),
            test_09_module,
        ),
        (
            TestDefinition(
                10,
                "Pacote de evidência",
                "Selecionar pacote elegível com publicação final (ou criar exemplo local).",
                "Listar candidatos, usar --package-id ou criar pacote de exemplo com hashes oficiais.",
                "Pacote existente com package_hash e merkle_root de 32 bytes.",
            ),
            test_10_package,
        ),
        (
            TestDefinition(
                11,
                "Gate de publicação final",
                "Garantir FINAL_ONTOLOGY_PUBLISHED (ou alias).",
                "is_final_publication_event no evento do anchor_request.",
                "Gate liberado: True.",
            ),
            test_11_gate,
        ),
        (
            TestDefinition(
                12,
                "Verificação off-chain inicial",
                "Validar integridade do pacote antes da ancoragem.",
                "VerifyEvidencePackageUseCase.execute.",
                "is_valid: True.",
            ),
            test_12_offchain,
        ),
        (
            TestDefinition(
                13,
                "Cálculos derivados",
                "Calcular evidence_key e idempotency_key oficiais.",
                "evidence_key_hex + build_idempotency_key + hex_hash_to_bytes32.",
                "Todos os bytes32 com 32 bytes.",
            ),
            test_13_derived,
        ),
        (
            TestDefinition(
                14,
                "Consulta on-chain antes da ancoragem",
                "Consultar se a evidência já existe no contrato.",
                "QueryAnchoredEvidenceUseCase + consulta Web3 independente.",
                "found True/False reportado corretamente.",
            ),
            test_14_pre_query,
        ),
        (
            TestDefinition(
                15,
                "Ancoragem real ou reaproveitamento",
                "Ancorar via caso de uso oficial ou retomar recibo.",
                "AnchorEvidencePackageUseCase com network_code=ethereum_sepolia.",
                "anchoring_status=confirmed e receipt_status=1, ou idempotent_reuse=True.",
            ),
            test_15_anchoring,
        ),
        (
            TestDefinition(
                16,
                "Recibo independente",
                "Consultar recibo da transação diretamente no RPC.",
                "eth.get_transaction_receipt e validações from/to/status.",
                "status==1; to==contrato; from==carteira.",
            ),
            test_16_receipt,
        ),
        (
            TestDefinition(
                17,
                "Evento EvidenceAnchored",
                "Decodificar o evento do recibo e comparar hashes.",
                "contract.events.EvidenceAnchored().process_receipt.",
                "Todos os event_*_match = True.",
            ),
            test_17_event,
        ),
        (
            TestDefinition(
                18,
                "Consulta on-chain após ancoragem",
                "Confirmar evidência on-chain via UC e Web3.py.",
                "QueryAnchoredEvidenceUseCase + evidenceExists/getEvidence.",
                "found=True e hashes coincidentes.",
            ),
            test_18_post_query,
        ),
        (
            TestDefinition(
                19,
                "Verificação completa",
                "Verificar off-chain + on-chain com o caso de uso oficial.",
                "VerifyAnchoredEvidenceUseCase.execute.",
                "overall_valid = True.",
            ),
            test_19_verify,
        ),
        (
            TestDefinition(
                20,
                "Idempotência",
                "Repetir ancoragem sem nova transação.",
                "Segunda chamada a AnchorEvidencePackageUseCase + nonce/DB.",
                "idempotent_reuse=True; hash/bloco/nonce inalterados.",
            ),
            test_20_idempotency,
        ),
        (
            TestDefinition(
                21,
                "Adulteração controlada",
                "Alterar cópia em memória e observar divergência de hash.",
                "deepcopy + to_canonical_json/sha256_hex vs hash on-chain.",
                "original_match=True; tampered_match=False.",
            ),
            test_21_tampering,
        ),
        (
            TestDefinition(
                22,
                "Revalidação do original",
                "Provar que a adulteração não alterou o pacote persistido.",
                "VerifyAnchoredEvidenceUseCase novamente no pacote original.",
                "overall_valid = True.",
            ),
            test_22_revalidate,
        ),
    ]

    try:
        for definition, fn in tests:
            # In query-only, still run read tests; write tests self-skip
            run_test(ctx, definition, fn)
    except UserAbortedError:
        write_summary_json(ctx, overall_ok=False)
        print(f"Estado parcial salvo em: {ctx.evidence_dir}")
        return 0
    except CriticalValidationError as exc:
        print(f"Validação interrompida. Evidências em: {ctx.evidence_dir}")
        if exc.recommendation:
            print(f"Recomendação: {exc.recommendation}")
        write_public_links(ctx)
        print_final_summary(ctx)
        return 1

    write_public_links(ctx)
    failed = sum(1 for r in ctx.results if r.status == TestStatus.FAILED)
    overall_ok = failed == 0
    write_summary_json(ctx, overall_ok=overall_ok)
    if overall_ok and not ctx.query_only and ctx.transaction_hash:
        write_validacao_executada(ctx)
    print_final_summary(ctx)
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
