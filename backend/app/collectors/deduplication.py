"""Idempotency and deduplication helpers for raw snapshots."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime for external snapshots."""
    return datetime.now(timezone.utc)


def normalize_for_hash(payload: Any) -> str:
    """Normalize arbitrary JSON-like data before hashing."""
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(payload: Any) -> str:
    """Return a deterministic SHA-256 hash for a raw payload."""
    return hashlib.sha256(normalize_for_hash(payload).encode("utf-8")).hexdigest()


def build_snapshot_key(
    *,
    source_key: str,
    canonical_artist_key: str,
    collector_key: str,
    payload: Any,
    captured_at: datetime | None = None,
) -> str:
    """Build an idempotent snapshot key from source, artist, collector and payload/date.

    The payload hash prevents duplicate storage when the exact same data is
    captured again. The UTC date keeps keys readable while still allowing a new
    snapshot when the payload changes.
    """
    captured = captured_at or utc_now()
    if captured.tzinfo is None:
        captured = captured.replace(tzinfo=timezone.utc)
    day = captured.astimezone(timezone.utc).date().isoformat()
    digest = content_hash(payload)[:16]
    return f"{source_key}:{canonical_artist_key}:{collector_key}:{day}:{digest}"
