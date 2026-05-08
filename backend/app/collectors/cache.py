"""Simple in-memory cache primitive for future controlled probes."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic
from typing import Any


@dataclass
class MemoryCache:
    """Tiny TTL cache used only for local scripts/probes.

    Persistent raw snapshots remain in PostgreSQL; this cache only prevents
    repeated calls inside one process when live probes are introduced.
    """

    ttl_seconds: int | None = 86_400
    _items: dict[str, tuple[float, Any]] = field(default_factory=dict)

    def get(self, key: str) -> Any | None:
        """Return a cached value or None when missing/expired."""
        item = self._items.get(key)
        if item is None:
            return None
        stored_at, value = item
        if self.ttl_seconds is not None and monotonic() - stored_at > self.ttl_seconds:
            self._items.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        """Store a value in the process-local cache."""
        self._items[key] = (monotonic(), value)
