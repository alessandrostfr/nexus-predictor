"""Pydantic schemas for the V2 evidence layer."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ConfidenceLevel = Literal["low", "medium", "high", "verified"]
EvidenceStatus = Literal["official", "confirmed", "estimated", "inferred", "pending_review"]
ExtractionMethod = Literal["manual", "json_seed", "api", "scraping", "computed", "user_evidence"]


class EvidenceORMModel(BaseModel):
    """Base schema configured to serialize SQLAlchemy model instances."""

    model_config = ConfigDict(from_attributes=True)


class SourceRecord(EvidenceORMModel):
    """Source registry row exposed through the API."""

    id: int
    key: str
    name: str
    source_type: str
    base_url: str | None = None
    default_confidence: str
    extraction_method: str
    is_active: bool
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class EvidenceItemRecord(EvidenceORMModel):
    """Atomic evidence item returned by evidence endpoints."""

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


class ArtistMetricRecord(EvidenceORMModel):
    """Aggregated metric attached to an artist."""

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


class PlatformProfileRecord(EvidenceORMModel):
    """Artist profile on a music/event platform."""

    id: int
    artist_slug: str
    platform: str
    profile_name: str | None = None
    profile_url: str | None = None
    external_id: str | None = None
    is_official: bool
    confidence: str


class SocialProfileRecord(EvidenceORMModel):
    """Artist profile on a social platform."""

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


class CareerEventRecord(EvidenceORMModel):
    """Artist career event exposed through the evidence API."""

    id: int
    artist_slug: str
    event_name: str
    event_type: str
    role: str | None = None
    country: str | None = None
    city: str | None = None
    venue_name: str | None = None
    event_date: str | None = None
    year: int | None = None
    is_headliner: bool
    confidence: str


class VenuePrestigeRecord(EvidenceORMModel):
    """Venue or festival prestige signal."""

    id: int
    slug: str
    name: str
    venue_type: str
    city: str | None = None
    country: str | None = None
    capacity: int | None = None
    prestige_score: float
    confidence: str
    notes: str | None = None


class ArtistEvidenceOverview(BaseModel):
    """Complete evidence overview for one artist."""

    artist_slug: str
    artist_name: str | None = None
    evidence_items: list[EvidenceItemRecord]
    metrics: list[ArtistMetricRecord]
    platform_profiles: list[PlatformProfileRecord]
    social_profiles: list[SocialProfileRecord]
    career_events: list[CareerEventRecord]


class EvidenceCoverage(BaseModel):
    """High-level counts used to validate V2.1 coverage."""

    artists: int
    artists_with_evidence: int
    sources: int
    evidence_items: int
    artist_metrics: int
    platform_profiles: int
    social_profiles: int
    career_events: int
    venue_prestige_items: int


class CreateManualEvidenceRequest(BaseModel):
    """Payload used to register user-provided or manually reviewed evidence."""

    artist_slug: str = Field(..., min_length=1, description="Existing artist slug, for example 'project-one'.")
    metric_key: str = Field(..., min_length=1, description="Metric name, for example 'manual.2025_room_correction'.")
    metric_value: str = Field(..., min_length=1, description="Evidence value stored as text for traceability.")
    source_name: str = Field(default="User-provided manual evidence")
    source_url: str | None = None
    confidence: ConfidenceLevel = "verified"
    status: EvidenceStatus = "confirmed"
    notes: str | None = Field(default=None, description="Manual note explaining the context and limits of the evidence.")
