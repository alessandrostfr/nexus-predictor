"""Minimal rate-limit policy guard for future collectors."""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.collectors.contracts import RateLimitPolicy


@dataclass
class RateLimiter:
    """Small synchronous limiter used by scripts/probes, not by pytest."""

    policy: RateLimitPolicy
    _last_call_at: float | None = None

    def wait(self) -> None:
        """Sleep when the policy defines a minimum delay."""
        if self.policy.min_delay_seconds is None:
            return
        now = time.monotonic()
        if self._last_call_at is not None:
            elapsed = now - self._last_call_at
            remaining = self.policy.min_delay_seconds - elapsed
            if remaining > 0:
                time.sleep(remaining)
        self._last_call_at = time.monotonic()
