"""Typed contracts shared by future V3.4 collectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CollectorStatus(StrEnum):
    """Allowed statuses for collectors, dry-runs and run items."""

    CONFIGURED = "configured"
    NOT_CONFIGURED = "not_configured"
    SKIPPED = "skipped"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    BLOCKED_BY_POLICY = "blocked_by_policy"
    TIMEOUT = "timeout"
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID_CREDENTIALS = "invalid_credentials"
    NOT_FOUND = "not_found"
    AMBIGUOUS_MATCH = "ambiguous_match"
    ACCESS_UNCONFIRMED = "access_unconfirmed"
    ACCESS_UNAVAILABLE = "access_unavailable"
    ALREADY_SEEN = "already_seen"


class CollectorRunStatus(StrEnum):
    """Allowed high-level states for collector runs."""

    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class RateLimitPolicy:
    """Human-readable rate-limit policy for one source or tool."""

    requests_per_minute: int | None = None
    min_delay_seconds: float | None = None
    quota_cost_hint: str | None = None
    burst_allowed: bool = False
    notes: str = ""

    def to_payload(self) -> dict[str, Any]:
        """Return a serializable payload for DB/API contracts."""
        return {
            "requests_per_minute": self.requests_per_minute,
            "min_delay_seconds": self.min_delay_seconds,
            "quota_cost_hint": self.quota_cost_hint,
            "burst_allowed": self.burst_allowed,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CachePolicy:
    """Cache contract for collectors.

    V3.4 requires cache policies before external calls are introduced. The
    policies here are contracts, not an in-memory implementation detail.
    """

    enabled: bool = True
    ttl_seconds: int | None = 86_400
    cache_key_fields: tuple[str, ...] = ("source_key", "canonical_artist_key", "collector_key")
    notes: str = "Cache must avoid repeated calls and protect quotas."

    def to_payload(self) -> dict[str, Any]:
        """Return a serializable cache contract."""
        return {
            "enabled": self.enabled,
            "ttl_seconds": self.ttl_seconds,
            "cache_key_fields": list(self.cache_key_fields),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class SourceCapability:
    """Capabilities exposed by a source for future feature engineering."""

    can_provide_followers: bool = False
    can_provide_plays: bool = False
    can_provide_tags: bool = False
    can_provide_bio: bool = False
    can_provide_events: bool = False
    can_provide_recent_activity: bool = False
    can_provide_profile_url: bool = True
    can_provide_images: bool = False
    can_provide_releases: bool = False

    def to_payload(self) -> dict[str, bool]:
        """Return a serializable capability matrix row."""
        return self.__dict__.copy()


@dataclass(frozen=True)
class CollectorContract:
    """Static contract for one external source collector."""

    collector_key: str
    source_key: str
    source_name: str
    source_type: str
    access_method: str
    extraction_method: str
    requires_credentials: bool
    credential_env_vars: tuple[str, ...] = ()
    rate_limit_policy: RateLimitPolicy = field(default_factory=RateLimitPolicy)
    cache_policy: CachePolicy = field(default_factory=CachePolicy)
    legal_risk: str = "unknown"
    ml_value: str = "medium"
    cost_level: str = "free_or_unknown"
    trust_level: str = "medium"
    confidence: str = "medium"
    supported_entities: tuple[str, ...] = ("artist",)
    can_run_without_credentials: bool = False
    collector_version: str = "v3.4-a"
    normalizer_version: str = "v3.4-a"
    schema_version: str = "v3.4"
    base_url: str | None = None
    requires_review: bool = False
    capabilities: SourceCapability = field(default_factory=SourceCapability)
    notes: str = ""

    def to_source_payload(self) -> dict[str, Any]:
        """Return sanitized metadata suitable for raw_sources.raw_payload."""
        return {
            "collector_key": self.collector_key,
            "requires_credentials": self.requires_credentials,
            "credential_env_vars": list(self.credential_env_vars),
            "rate_limit_policy": self.rate_limit_policy.to_payload(),
            "cache_policy": self.cache_policy.to_payload(),
            "supported_entities": list(self.supported_entities),
            "can_run_without_credentials": self.can_run_without_credentials,
            "collector_version": self.collector_version,
            "normalizer_version": self.normalizer_version,
            "schema_version": self.schema_version,
            "capabilities": self.capabilities.to_payload(),
            "no_secret_values_stored": True,
        }


@dataclass(frozen=True)
class ToolEvaluationContract:
    """Static evaluation of an API, extractor, scraper or manual fallback."""

    tool_key: str
    source_target: str
    source_key: str | None
    tool_name: str
    tool_type: str
    candidate_for: str
    access_method: str
    license_name: str | None
    license_risk: str
    legal_risk: str
    maintenance_status: str
    integration_complexity: str
    data_quality_expectation: str
    ml_value: str
    decision: str
    decision_reason: str
    docs_url: str | None = None
    repo_url: str | None = None
    supports_cache: bool = True
    supports_rate_limit: bool = True
    requires_credentials: bool = False
    requires_manual_review: bool = False
    evaluation_payload: dict[str, Any] = field(default_factory=dict)
