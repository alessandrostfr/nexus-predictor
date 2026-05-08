"""Schemas for V3.4 external-ingestion architecture endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class V34CapabilityMatrix(BaseModel):
    """Capability flags advertised by one source."""

    can_provide_followers: bool = False
    can_provide_plays: bool = False
    can_provide_tags: bool = False
    can_provide_bio: bool = False
    can_provide_events: bool = False
    can_provide_recent_activity: bool = False
    can_provide_profile_url: bool = False
    can_provide_images: bool = False
    can_provide_releases: bool = False


class V34CollectorSourceRecord(BaseModel):
    """Sanitized source/collector contract returned by the API."""

    source_key: str
    collector_key: str
    source_name: str
    source_type: str
    access_method: str
    extraction_method: str
    requires_credentials: bool
    credential_env_vars: list[str]
    credential_status: dict[str, str] = Field(default_factory=dict)
    rate_limit_policy: dict[str, object]
    cache_policy: dict[str, object]
    legal_risk: str
    ml_value: str
    cost_level: str
    trust_level: str
    confidence: str
    supported_entities: list[str]
    can_run_without_credentials: bool
    collector_version: str
    normalizer_version: str
    schema_version: str
    capabilities: V34CapabilityMatrix
    configured_status: str
    notes: str | None = None


class V34SourceListResponse(BaseModel):
    """Source registry list response."""

    total: int
    configured: int
    not_configured: int
    sources: list[V34CollectorSourceRecord]


class V34ToolEvaluationRecord(BaseModel):
    """Sanitized tool evaluation returned by the API."""

    tool_key: str
    source_target: str
    source_key: str | None
    tool_name: str
    tool_type: str
    candidate_for: str
    access_method: str
    license_name: str | None = None
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
    supports_cache: bool
    supports_rate_limit: bool
    requires_credentials: bool
    requires_manual_review: bool
    evaluation_payload: dict[str, object] = Field(default_factory=dict)


class V34ToolEvaluationListResponse(BaseModel):
    """Tool evaluation registry list response."""

    total: int
    evaluated_not_integrated: int
    requires_manual_review: int
    tools: list[V34ToolEvaluationRecord]


class V34ArchitectureTable(BaseModel):
    """Database object required by V3.4-A."""

    table_name: str
    purpose: str
    rows: int
    required_for: str


class V34ArchitectureResponse(BaseModel):
    """High-level V3.4-A architecture contract."""

    block: str = "V3.4-A"
    ready: bool
    no_external_calls_in_tests: bool = True
    no_secrets_in_api: bool = True
    dry_run_persists_external_data: bool = False
    collector_package: list[str]
    statuses: list[str]
    run_statuses: list[str]
    tables: list[V34ArchitectureTable]
    warnings: list[str] = Field(default_factory=list)


class V34DryRunRequest(BaseModel):
    """Dry-run request used to validate scope and configured sources."""

    artist_scope: str = "nexus_2026"
    limit: int | None = Field(default=5, ge=1, le=500)
    sources: list[str] | None = None
    started_by: str = "local_validation"


class V34DryRunResponse(BaseModel):
    """Dry-run response that must not persist raw snapshots or metrics."""

    dry_run: bool = True
    artist_scope: str
    artist_count: int
    selected_artist_count: int
    selected_sources: list[str]
    configured_sources: list[str]
    not_configured_sources: list[str]
    blocked_sources: list[str]
    warnings: list[str]
    would_persist_raw_snapshots: bool = False
    would_persist_normalized_metrics: bool = False
    manifest: dict[str, object]
