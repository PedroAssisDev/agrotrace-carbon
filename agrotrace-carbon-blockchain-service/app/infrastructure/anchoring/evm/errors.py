"""EVM-specific exceptions (sanitized — never include private keys)."""

from __future__ import annotations

from app.shared.exceptions import AnchoringProviderError, ConfigurationError


class EvmProviderError(AnchoringProviderError):
    """Base EVM provider error."""


class RpcUnavailableError(EvmProviderError):
    pass


class ChainIdMismatchError(EvmProviderError):
    pass


class ContractMissingError(EvmProviderError):
    pass


class InvalidAbiError(EvmProviderError):
    pass


class InvalidAddressError(EvmProviderError):
    pass


class PrivateKeyMissingError(ConfigurationError):
    pass


class PrivateKeyInvalidError(ConfigurationError):
    pass


class WalletNotAuthorizedError(EvmProviderError):
    pass


class InsufficientBalanceError(EvmProviderError):
    pass


class GasEstimationError(EvmProviderError):
    pass


class NonceError(EvmProviderError):
    pass


class TransactionRevertedError(EvmProviderError):
    pass


class ReceiptTimeoutError(EvmProviderError):
    pass


class DuplicateEvidenceError(EvmProviderError):
    pass


class OnchainMismatchError(EvmProviderError):
    pass
