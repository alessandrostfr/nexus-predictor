"""Base class for future source collectors."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.collectors.contracts import CollectorContract, CollectorStatus


@dataclass(frozen=True)
class CollectorResult:
    """Result returned by a collector without assuming persistence."""

    status: CollectorStatus
    raw_payload: dict[str, Any] | None = None
    normalized_metrics: list[dict[str, Any]] | None = None
    safe_message: str | None = None


class BaseCollector:
    """Base contract for collectors introduced in later V3.4 macropasos."""

    contract: CollectorContract

    def __init__(self, contract: CollectorContract) -> None:
        self.contract = contract

    def collect(self, canonical_artist_key: str, *, dry_run: bool = True) -> CollectorResult:
        """Collect external data for one artist.

        V3.4-A only defines the interface. Concrete collectors are implemented
        in V3.4-B/C after credentials and tool policies are validated.
        """
        return CollectorResult(
            status=CollectorStatus.SKIPPED,
            safe_message=f"Collector {self.contract.collector_key} is an architecture contract only in V3.4-A.",
        )
