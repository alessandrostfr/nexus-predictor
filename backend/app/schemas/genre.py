"""Schemas for hard dance genre classification endpoints."""

from pydantic import BaseModel, Field


class GenreDefinition(BaseModel):
    """One genre in the MVP hard dance taxonomy."""

    name: str
    parent: str | None = None
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)
    priority: int = 0


class GenreSeed(BaseModel):
    """Genre count used by the legacy and classified distribution endpoints."""

    name: str
    artist_count: int
    parent: str | None = None
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)


class ClassifiedArtistGenre(BaseModel):
    """One artist after rule-based genre classification."""

    slug: str
    name: str
    normalized_name: str
    main_genre: str = "Unknown"
    primary_genre_seed: str = "Unknown"
    genre_source: str = "unknown"
    confidence: str = "low"
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
