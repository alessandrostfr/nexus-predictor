"""Schemas for hard dance genre classification endpoints.

V2.5 keeps the old response fields for compatibility, but adds multi-genre
fields so the frontend and later model blocks can use chips, confidence and
source-level traceability.
"""

from pydantic import BaseModel, Field


class GenreDefinition(BaseModel):
    """One genre in the Nexus hard-dance taxonomy."""

    name: str
    parent: str | None = None
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    priority: int = 0


class GenreSeed(BaseModel):
    """Genre count used by distribution endpoints."""

    name: str
    artist_count: int
    parent: str | None = None
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)


class GenreSourceRecord(BaseModel):
    """One traceable source contributing to a V2.5 genre decision."""

    source_type: str
    source_name: str
    metric_key: str
    confidence: str = "medium"
    weight: float = 0.0
    evidence_id: int | None = None
    source_url: str | None = None
    matched_value: str | None = None
    notes: str | None = None


class ClassifiedArtistGenre(BaseModel):
    """One artist after V2 multi-genre classification."""

    slug: str
    name: str
    normalized_name: str
    main_genre: str = "Unknown"
    secondary_genres: list[str] = Field(default_factory=list)
    primary_genre_seed: str = "Unknown"

    # Compatibility fields used by the V1/V2 frontend and old tests.
    genre_source: str = "unknown"
    confidence: str = "low"

    # V2.5 fields.
    genre_confidence: str = "low"
    genre_confidence_score: float = 0.0
    genre_sources: list[GenreSourceRecord] = Field(default_factory=list)
    reason: str | None = None
    matched_keywords: list[str] = Field(default_factory=list)

    appearance_count: int = 0
    appearance_years: list[int] = Field(default_factory=list)
    manual_review: bool = False
    needs_manual_review: bool = False
    artist_kind: str = "artist"
    is_special_show: bool = False
    related_canonical_artists: list[str] = Field(default_factory=list)


class ClassifiedArtistGenreList(BaseModel):
    """Paginated classified artist response."""

    total: int
    limit: int
    offset: int
    items: list[ClassifiedArtistGenre]


class EditionGenreDistribution(BaseModel):
    """Classified genre distribution for one edition."""

    year: int
    distribution: list[GenreSeed]
    total_artists: int = 0
    classified_artists: int = 0
    unknown_artists: int = 0


class GenreTaxonomyResponse(BaseModel):
    """Full taxonomy payload."""

    taxonomy: list[GenreDefinition]
    total: int


class MultiGenreCoverage(BaseModel):
    """Coverage report for the V2.5 multi-genre layer."""

    total_artists: int
    classified_artists: int
    unknown_artists: int
    classified_ratio: float
    low_confidence_artists: int
    artists_needing_review: int
    artists_with_secondary_genres: int
    persisted_genre_rows: int


class MultiGenreRebuildResult(BaseModel):
    """Result returned after rebuilding persisted artist_genres rows."""

    artists_processed: int
    genre_rows: int
    evidence_items: int
    artist_metrics: int
    coverage: MultiGenreCoverage


class GenreComparisonRecord(BaseModel):
    """V1 seed vs V2 multi-genre comparison for one artist."""

    artist_slug: str
    artist_name: str
    v1_primary_genre: str
    v2_main_genre: str
    v2_secondary_genres: list[str] = Field(default_factory=list)
    confidence: str
    changed: bool
    needs_manual_review: bool


class GenreComparisonResponse(BaseModel):
    """Comparison summary between V1 primary_genre_seed and V2.5."""

    total: int
    changed: int
    unknown_reduced: int
    items: list[GenreComparisonRecord]
