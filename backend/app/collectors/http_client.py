"""HTTP client contract for future collectors.

V3.4-A intentionally does not perform network calls from tests. This wrapper is
kept small so later probes can share timeout/rate-limit/cache policy without
leaking secrets or bypassing extraction rules.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.collectors.errors import CollectorError


class CollectorHttpClient:
    """Safe synchronous HTTP helper for controlled scripts/probes."""

    def __init__(self, *, timeout_seconds: float = 12.0) -> None:
        self.timeout_seconds = timeout_seconds

    def get_json(self, url: str, *, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Fetch JSON and convert failures into collector-safe errors."""
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, headers=headers, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise CollectorError(f"HTTP collector request failed: {exc.__class__.__name__}") from exc
        except ValueError as exc:
            raise CollectorError("HTTP collector response was not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise CollectorError("HTTP collector response must be a JSON object.")
        return payload
