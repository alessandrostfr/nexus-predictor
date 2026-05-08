"""V3.4 collector foundation.

This package contains architecture contracts only in V3.4-A. Real network/API
collectors are intentionally deferred to the next macropasos so pytest remains
fully offline and deterministic.
"""

from app.collectors.contracts import CollectorContract, CollectorStatus
from app.collectors.registry import COLLECTOR_REGISTRY, TOOL_EVALUATION_REGISTRY

__all__ = [
    "CollectorContract",
    "CollectorStatus",
    "COLLECTOR_REGISTRY",
    "TOOL_EVALUATION_REGISTRY",
]
