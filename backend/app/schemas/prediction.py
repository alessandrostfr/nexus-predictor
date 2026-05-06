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
