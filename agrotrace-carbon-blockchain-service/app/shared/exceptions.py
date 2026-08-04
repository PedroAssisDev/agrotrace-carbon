class BlockchainServiceError(Exception):
    """Base error for blockchain service."""


class NotFoundError(BlockchainServiceError):
    """Entity not found."""


class InvalidStateError(BlockchainServiceError):
    """Invalid entity state for requested operation."""


class ProvenanceReadError(BlockchainServiceError):
    """Error reading from provenance service."""


class VerificationError(BlockchainServiceError):
    """Evidence verification failed."""
