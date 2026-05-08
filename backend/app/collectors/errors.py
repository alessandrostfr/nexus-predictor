"""Controlled exceptions for the V3 collector layer."""

from __future__ import annotations

from app.collectors.contracts import CollectorStatus


class CollectorError(RuntimeError):
    """Base collector error that can be safely transformed into a run item."""

    def __init__(self, message: str, *, status: CollectorStatus = CollectorStatus.FAILED) -> None:
        super().__init__(message)
        self.status = status
        self.safe_message = message


class CollectorPolicyError(CollectorError):
    """Raised when a collector is blocked by the extraction policy."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status=CollectorStatus.BLOCKED_BY_POLICY)


class CollectorCredentialError(CollectorError):
    """Raised when required credentials are missing or invalid."""

    def __init__(self, message: str = "Required credentials are missing or invalid.") -> None:
        super().__init__(message, status=CollectorStatus.NOT_CONFIGURED)
