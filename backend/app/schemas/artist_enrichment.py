"""Pydantic schemas for enriched artist profiles."""

from typing import Any

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    """Source metadata attached to every important external field."""

    source: str
    source_url: str | None = None
    captured_at: str | None = None
    confidence: str = "pending"
    notes: str | None = None


class ArtistExternalIds(BaseModel):
    """External identifiers discovered during enrichment."""

    spotify_id: str | None = None
    musicbrainz_id: str | None = None
    lastfm_name: str | None = None


class ArtistTrack(BaseModel):
    """Track payload used for top tracks and latest releases."""

    title: str
    artist_name: str | None = None
    source: str
    listeners: int | None = None
    playcount: int | None = None
    release_date: str | None = None
    album_name: str | None = None
    external_url: str | None = None
    image_url: str | None = None


class ArtistRelease(BaseModel):
    """Recent release payload."""

    title: str
    release_type: str | None = None
    release_date: str | None = None
    source: str
    external_url: str | None = None
    image_url: str | None = None


class ArtistProfile(BaseModel):
    """Complete artist profile returned to the frontend."""

    slug: str
    name: str
    normalized_name: str
    primary_genre_seed: str = "Unknown"
    appearance_count: int = 0
    appearance_years: list[int] = Field(default_factory=list)
    appearances: list[dict[str, Any]] = Field(default_factory=list)
    manual_review: bool = False

    data_status: str = "pending_external_enrichment"
    image_url: str | None = None
    bio: str | None = None
    bio_source_url: str | None = None
    country: str | None = None
    external_links: dict[str, str] = Field(default_factory=dict)
    external_ids: ArtistExternalIds = Field(default_factory=ArtistExternalIds)
    aliases: list[str] = Field(default_factory=list)
    top_tracks: list[ArtistTrack] = Field(default_factory=list)
    latest_releases: list[ArtistRelease] = Field(default_factory=list)
    sources: list[SourceReference] = Field(default_factory=list)
    enrichment_notes: list[str] = Field(default_factory=list)
    last_enriched_at: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class ArtistProfileList(BaseModel):
    """Paginated artist profile list payload."""

    total: int
    limit: int
    offset: int
    items: list[ArtistProfile]


class ArtistRefreshResult(BaseModel):
    """Payload returned after trying to refresh one artist profile."""

    slug: str
    refreshed: bool
    external_calls_enabled: bool
    profile: ArtistProfile
    warnings: list[str] = Field(default_factory=list)
