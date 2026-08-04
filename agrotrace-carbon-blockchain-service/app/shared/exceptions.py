class BlockchainServiceError(Exception):
    """Base error for blockchain service."""


class NotFoundError(BlockchainServiceError):
    """Entity not found."""


class InvalidStateError(BlockchainServiceError):
    """Invalid entity state for requested operation."""


class FinalPublicationRequiredError(InvalidStateError):
    """Anchoring requires a final ontology publication event."""


class ProvenanceReadError(BlockchainServiceError):
    """Error reading from provenance service."""


class VerificationError(BlockchainServiceError):
    """Evidence verification failed."""


class AnchoringProviderError(BlockchainServiceError):
    """Provider-level anchoring failure (RPC, gas, revert, etc.)."""


class ConfigurationError(BlockchainServiceError):
    """Missing or invalid blockchain configuration."""
