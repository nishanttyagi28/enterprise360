"""Domain exceptions: callers can distinguish bad input (do not retry) from infra failures."""


class IngestionError(Exception):
    """Base class for ingestion failures."""


class SourceFileMissingError(IngestionError):
    """A file required by a contract is not present."""


class ContractViolationError(IngestionError):
    """A file does not match its schema contract (header mismatch, empty file...)."""
