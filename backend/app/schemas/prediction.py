"""Schemas for predictive scoring endpoints.

The Block 5 model is deliberately interpretable. Every score returned by the API
contains its factor breakdown so the user can understand why an artist or an
edition receives a high, medium or low prediction.
"""

from typing import Any

from pydantic import BaseModel, Field


class PredictionFactor(BaseModel):
    """One interpretable contribution used by the scoring engine."""

    key: str
    label: str
    contribution: float
    max_contribution: float
    explanation: str


class ArtistDemandPrediction(BaseModel):
    """Demand prediction for one artist or special show."""

    year: int
    slug: str
    name: str
    rank: int | None = None
    main_genre: str = "Unknown"
    artist_kind: str = "artist"
    is_special_show: bool = False
    demand_score: float = Field(ge=0, le=100)
    crowd_risk: str
    confidence: str
    performance_names: list[str] = Field(default_factory=list)
    performance_types: list[str] = Field(default_factory=list)
    appearance_count: int = 0
    previous_appearance_years: list[int] = Field(default_factory=list)
    factors: list[PredictionFactor] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class ArtistDemandPredictionList(BaseModel):
    """Paginated artist demand ranking."""

    year: int
    total: int
    limit: int
    offset: int
    items: list[ArtistDemandPrediction]


class AttendancePrediction(BaseModel):
    """Attendance forecast for one Nexus edition."""

    year: int
    predicted_low: int
    predicted_mid: int
    predicted_high: int
    confidence: str
    method: str
    baseline_years: list[int] = Field(default_factory=list)
    factors: list[PredictionFactor] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class GenreDistributionPredictionItem(BaseModel):
    """Compact genre distribution item used by prediction payloads.

    The Block 4 taxonomy contains extra metadata such as aliases and parent
    relations. Predictions only need a stable compact summary so snapshots and
    API responses stay frontend-friendly.
    """

    name: str
    artist_count: int = 0
    percentage: float | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class EditionPrediction(BaseModel):
    """Full prediction payload for an edition."""

    year: int
    edition_name: str
    generated_at: str
    source_status: str
    attendance: AttendancePrediction
    top_artist_predictions: list[ArtistDemandPrediction]
    genre_distribution: list[GenreDistributionPredictionItem] = Field(default_factory=list)
    total_artist_predictions: int


class V2DemandFeature(BaseModel):
    """One normalized feature used by the V2.7 model."""

    key: str
    label: str
    value: float | str | bool | None = None
    normalized_value: float = Field(ge=0, le=100)
    source_metric: str | None = None
    confidence: str = "medium"
    explanation: str


class V2DemandScoreBreakdown(BaseModel):
    """Separated V2.7 score components."""

    popularity_score: float = Field(ge=0, le=100)
    career_score: float = Field(ge=0, le=100)
    momentum_score: float = Field(ge=0, le=100)
    nexus_affinity_score: float = Field(ge=0, le=100)
    demand_score: float = Field(ge=0, le=100)


class V2DemandPrediction(BaseModel):
    """V2.7 demand prediction for one artist with feature traceability."""

    year: int
    artist_slug: str
    artist_name: str
    rank: int | None = None
    main_genre: str = "Unknown"
    secondary_genres: list[str] = Field(default_factory=list)
    popularity_score: float = Field(ge=0, le=100)
    career_score: float = Field(ge=0, le=100)
    momentum_score: float = Field(ge=0, le=100)
    nexus_affinity_score: float = Field(ge=0, le=100)
    demand_score: float = Field(ge=0, le=100)
    crowd_risk: str
    confidence: str
    model_version: str
    method: str
    fallback_used: bool = False
    evidence_count: int = 0
    features: list[V2DemandFeature] = Field(default_factory=list)
    factors: list[PredictionFactor] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    generated_at: str


class V2DemandPredictionList(BaseModel):
    """Paginated V2.7 demand ranking."""

    year: int
    total: int
    limit: int
    offset: int
    items: list[V2DemandPrediction]


class V2DemandModelCoverage(BaseModel):
    """Coverage and quality counters for the V2.7 model."""

    year: int
    total_artists: int
    persisted_predictions: int
    artists_with_external_metrics: int
    artists_with_spotify: int
    artists_with_social_or_platform_metrics: int
    artists_with_career_signals: int
    artists_with_historical_timetable: int
    fallback_predictions: int
    average_demand_score: float
    model_version: str
    method: str
    generated_at: str | None = None


class V2DemandRebuildResult(BaseModel):
    """Result of rebuilding V2.7 predictions."""

    year: int
    model_version: str
    predictions: int
    fallback_predictions: int
    top_artist_slug: str | None = None
    top_artist_score: float | None = None
    generated_at: str


class V2ModelComparisonItem(BaseModel):
    """One V1/V2 comparison row."""

    artist_slug: str
    artist_name: str
    v1_rank: int | None = None
    v1_demand_score: float | None = None
    v2_rank: int | None = None
    v2_demand_score: float | None = None
    delta: float | None = None
    main_reason: str


class V2ModelComparisonResponse(BaseModel):
    """Comparison between the old V1 scoring endpoint and V2.7."""

    year: int
    total: int
    limit: int
    items: list[V2ModelComparisonItem]
