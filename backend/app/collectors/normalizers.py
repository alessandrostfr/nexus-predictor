"""Shared normalizer helpers for external metrics."""

from __future__ import annotations

from typing import Any


def safe_int(value: Any) -> int | None:
    """Return a non-negative integer or None for invalid values."""
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def safe_float(value: Any) -> float | None:
    """Return a non-negative float or None for invalid values."""
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def feature_candidate_from_confidence(confidence: str, match_status: str | None = None) -> bool:
    """Apply the V3 identity/quality gate for future feature candidates."""
    allowed_confidence = confidence in {"verified", "high"}
    allowed_status = match_status in (None, "verified", "high")
    return allowed_confidence and allowed_status
