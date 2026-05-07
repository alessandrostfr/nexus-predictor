"""Pydantic schemas for Nexus Predictor V2.2 Spotify enrichment."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SpotifyORMModel(BaseModel):
    """Base schema configured for SQLAlchemy model serialization."""

    model_config = ConfigDict(from_attributes=True)


class SpotifyStatus(BaseModel):
    """Safe public status for the Spotify integration."""

    configured: bool
    token_url: str
    api_base_url: str
    default_market: str
    artist_search_limit: int
    top_track_limit: int
    release_limit: int
    credentials_hint: str


class SpotifyTrackRecord(BaseModel):
    """Compact Spotify top-track record stored in cache/evidence."""

    id: str | None = None
    title: str
    popularity: int | None = None
    preview_url: str | None = None
    spotify_url: str | None = None
    album_name: str | None = None
    release_date: str | None = None
    duration_ms: int | None = None
    explicit: bool | None = None


class SpotifyReleaseRecord(BaseModel):
    """Compact Spotify release record stored in cache/evidence."""

    id: str | None = None
    title: str
    release_type: str | None = None
    release_date: str | None = None
    total_tracks: int | None = None
    spotify_url: str | None = None
    image_url: str | None = None


class SpotifyArtistCacheRecord(SpotifyORMModel):
    """Public API representation of a cached Spotify artist match."""

    id: int
    artist_slug: str
    spotify_artist_id: str
    spotify_url: str | None = None
    spotify_uri: str | None = None
    embed_url: str | None = None
    name: str
    avatar_url: str | None = None
    popularity: int | None = None
    followers: int | None = None
    genres: list[str] = Field(default_factory=list)
    top_tracks: list[SpotifyTrackRecord] = Field(default_factory=list)
    releases: list[SpotifyReleaseRecord] = Field(default_factory=list)
    match_confidence: str
    match_method: str
    last_refreshed_at: datetime


class SpotifyRefreshResult(BaseModel):
    """Result returned when one artist is refreshed from Spotify."""

    artist_slug: str
    refreshed: bool
    cached: bool
    configured: bool
    message: str
    spotify_artist: SpotifyArtistCacheRecord | None = None
    evidence_items_created: int = 0
    metrics_upserted: int = 0
    warnings: list[str] = Field(default_factory=list)


class SpotifyRefreshBatchResult(BaseModel):
    """Result returned when several artists are refreshed."""

    requested: int
    refreshed: int
    skipped: int
    failed: int
    results: list[SpotifyRefreshResult]
    errors: list[str] = Field(default_factory=list)


class SpotifyArtistSearchResult(BaseModel):
    """Raw candidate returned from Spotify search for review/debugging."""

    spotify_artist_id: str
    name: str
    popularity: int | None = None
    followers: int | None = None
    genres: list[str] = Field(default_factory=list)
    spotify_url: str | None = None
    score: float
    raw: dict[str, Any] = Field(default_factory=dict)
