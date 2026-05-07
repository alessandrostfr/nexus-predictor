"""Pydantic schemas for V2.4 social and music-platform ingestion."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SocialPlatformORMModel(BaseModel):
    """Base model that can serialize SQLAlchemy rows."""

    model_config = ConfigDict(from_attributes=True)


class SocialPlatformStatus(BaseModel):
    """Safe public status for V2.4 integrations."""

    lastfm: dict[str, Any]
    manual_json_seed_exists: bool
    manual_csv_seed_exists: bool
    supported_social_platforms: list[str]
    supported_music_platforms: list[str]


class SocialPlatformCoverage(BaseModel):
    """Coverage and freshness summary for social/platform metrics."""

    sources: int
    social_profiles: int
    platform_profiles: int
    social_evidence_items: int
    social_artist_metrics: int
    artists_with_social_profiles: int
    artists_with_platform_profiles: int
    artists_with_scores: int
    lastfm_configured: bool
    latest_social_capture_at: datetime | None = None


class SocialPlatformRunSummary(BaseModel):
    """Summary returned after mixed JSON/CSV ingestion."""

    sources: int
    social_profiles: int
    platform_profiles: int
    evidence_items: int
    artist_metrics: int
    artists_processed: int
    manual_csv_rows: int
    warnings: list[str] = Field(default_factory=list)


class SocialProfileRecord(SocialPlatformORMModel):
    """Social profile row exposed by V2.4 endpoints."""

    id: int
    artist_slug: str
    platform: str
    handle: str | None = None
    profile_url: str | None = None
    follower_count: int | None = None
    engagement_rate: float | None = None
    average_views: int | None = None
    last_post_at: datetime | None = None
    is_official: bool
    confidence: str


class PlatformProfileRecord(SocialPlatformORMModel):
    """Music-platform profile row exposed by V2.4 endpoints."""

    id: int
    artist_slug: str
    platform: str
    profile_name: str | None = None
    profile_url: str | None = None
    external_id: str | None = None
    is_official: bool
    confidence: str


class SocialMetricRecord(SocialPlatformORMModel):
    """Derived social/platform metric row."""

    id: int
    artist_slug: str
    metric_key: str
    metric_value_numeric: float | None = None
    metric_value_text: str | None = None
    value_type: str
    confidence: str
    evidence_count: int
    latest_captured_at: datetime | None = None
    notes: str | None = None


class SocialEvidenceRecord(SocialPlatformORMModel):
    """Atomic social/platform evidence row."""

    id: int
    artist_slug: str | None = None
    source_type: str
    source_name: str
    source_url: str | None = None
    captured_at: datetime
    metric_key: str
    metric_value: str
    value_type: str
    confidence: str
    extraction_method: str
    evidence_kind: str
    status: str
    notes: str | None = None


class ArtistSocialOverview(BaseModel):
    """Complete V2.4 social/platform view for one artist."""

    artist_slug: str
    artist_name: str
    social_profiles: list[SocialProfileRecord]
    platform_profiles: list[PlatformProfileRecord]
    metrics: list[SocialMetricRecord]
    evidence_items: list[SocialEvidenceRecord]


class LastfmRefreshResult(BaseModel):
    """Result from refreshing one artist from Last.fm."""

    artist_slug: str
    configured: bool
    refreshed: bool
    message: str
    top_tracks: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
