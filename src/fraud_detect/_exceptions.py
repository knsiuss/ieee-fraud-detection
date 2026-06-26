"""Domain-specific exceptions for the fraud detection toolkit."""

from __future__ import annotations

class FraudDetectError(Exception):
    """Base exception for all fraud_detect errors."""

class MissingArtefactError(FraudDetectError, FileNotFoundError):
    """Raised when a required data artefact (parquet, CSV) is not found.

    Examples
    --------
    >>> raise MissingArtefactError("train_merged.parquet")
    Traceback (most recent call last):
    ...
    MissingArtefactError: train_merged.parquet
    """

class InvalidDataError(FraudDetectError, ValueError):
    """Raised when data fails schema or validation checks."""
