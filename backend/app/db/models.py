"""SQLAlchemy models for Nexus Predictor.

The original V1 tables keep the API compatible with the MVP endpoints while V2
adds a real evidence layer. The V2 layer is deliberately explicit: every metric
that may influence popularity, trajectory, genre confidence or timetable models
can be traced back to a source, URL, capture date, confidence level and notes.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class EditionModel(Base):
    """One Nexus Festival edition loaded from an editable JSON file."""

    __tablename__ = "editions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")
    venue: Mapped[str] = mapped_column(String(255), nullable=False, default="Fabrik Madrid")
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_start: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date_end: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration_hours: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artist_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attendance_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    lineup_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    sources_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class ArtistModel(Base):
    """Normalized artist entry created from the historical lineups."""

    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_genre_seed: Mapped[str] = mapped_column(String(120), nullable=False, default="Unknown")
    appearance_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    data_status: Mapped[str] = mapped_column(String(120), nullable=False, default="seed_from_lineup")
    appearance_years_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    appearances_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class RoomModel(Base):
    """Fabrik room or area with editable capacity ranges."""

    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    min_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[str] = mapped_column(String(80), nullable=False, default="pending")
    aliases_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    source_keys_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class DatasetMetaModel(Base):
    """Small key/value table used to track seed status."""

    __tablename__ = "dataset_meta"
    __table_args__ = (UniqueConstraint("key", name="uq_dataset_meta_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class SourceModel(Base):
    """Registry of public, internal and manual data sources.

    A source is the stable identity of where evidence comes from. Individual
    evidence rows can still store a source URL because one source may produce
    multiple pages, API responses or manual entries.
    """

    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("key", name="uq_sources_key"),
        Index("ix_sources_type_confidence", "source_type", "default_confidence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, default="internal")
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    extraction_method: Mapped[str] = mapped_column(String(80), nullable=False, default="manual")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class EvidenceItemModel(Base):
    """Atomic evidence used by V2 metrics and future model features."""

    __tablename__ = "evidence_items"
    __table_args__ = (
        Index("ix_evidence_artist_metric", "artist_slug", "metric_key"),
        Index("ix_evidence_source_confidence", "source_type", "confidence"),
        Index("ix_evidence_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artist_id: Mapped[int | None] = mapped_column(
        ForeignKey("artists.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    artist_slug: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    metric_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    metric_value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(40), nullable=False, default="text")
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    extraction_method: Mapped[str] = mapped_column(String(80), nullable=False, default="manual")
    evidence_kind: Mapped[str] = mapped_column(String(80), nullable=False, default="metric")
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="confirmed")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class ArtistMetricModel(Base):
    """Aggregated metric derived from one or more evidence items."""

    __tablename__ = "artist_metrics"
    __table_args__ = (
        UniqueConstraint("artist_slug", "metric_key", name="uq_artist_metrics_artist_metric"),
        Index("ix_artist_metrics_metric_confidence", "metric_key", "confidence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artist_id: Mapped[int | None] = mapped_column(
        ForeignKey("artists.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    artist_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    metric_key: Mapped[str] = mapped_column(String(160), nullable=False)
    metric_value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_type: Mapped[str] = mapped_column(String(40), nullable=False, default="number")
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latest_captured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class PlatformProfileModel(Base):
    """Artist profile on a music or event platform.

    Spotify, YouTube, Beatport, 1001Tracklists, Resident Advisor and similar
    platforms will be filled progressively by later V2 blocks.
    """

    __tablename__ = "platform_profiles"
    __table_args__ = (
        UniqueConstraint("artist_slug", "platform", "profile_url", name="uq_platform_profile_url"),
        Index("ix_platform_profiles_platform", "platform"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), nullable=True)
    artist_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(80), nullable=False)
    profile_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SocialProfileModel(Base):
    """Artist profile and counters on social networks."""

    __tablename__ = "social_profiles"
    __table_args__ = (
        UniqueConstraint("artist_slug", "platform", "profile_url", name="uq_social_profile_url"),
        Index("ix_social_profiles_platform", "platform"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), nullable=True)
    artist_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(80), nullable=False)
    handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    follower_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    engagement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_views: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_post_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class CareerEventModel(Base):
    """Artist career signal: event, club, festival, venue or headline role."""

    __tablename__ = "career_events"
    __table_args__ = (
        Index("ix_career_events_artist_year", "artist_slug", "year"),
        Index("ix_career_events_event_type", "event_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), nullable=True)
    artist_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, default="festival")
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    venue_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    event_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_headliner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class VenuePrestigeModel(Base):
    """Prestige registry for clubs, festivals and rooms used by V2 features."""

    __tablename__ = "venue_prestige"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_venue_prestige_slug"),
        Index("ix_venue_prestige_type_score", "venue_type", "prestige_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    venue_type: Mapped[str] = mapped_column(String(80), nullable=False, default="venue")
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prestige_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class SpotifyArtistCacheModel(Base):
    """Cached Spotify enrichment payload for one Nexus artist.

    The table stores the public Spotify artist match, display fields and compact
    JSON snapshots for top tracks/releases. Atomic values that influence the
    model are still duplicated into `evidence_items` and `artist_metrics` so the
    feature layer remains explainable.
    """

    __tablename__ = "spotify_artist_cache"
    __table_args__ = (
        UniqueConstraint("artist_slug", name="uq_spotify_artist_cache_artist_slug"),
        UniqueConstraint("spotify_artist_id", name="uq_spotify_artist_cache_spotify_artist_id"),
        Index("ix_spotify_artist_cache_popularity", "popularity"),
        Index("ix_spotify_artist_cache_match_confidence", "match_confidence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), nullable=True)
    artist_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    spotify_artist_id: Mapped[str] = mapped_column(String(255), nullable=False)
    spotify_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    spotify_uri: Mapped[str | None] = mapped_column(String(255), nullable=True)
    embed_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    followers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    genres_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    top_tracks_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    releases_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    match_confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    match_method: Mapped[str] = mapped_column(String(80), nullable=False, default="spotify_search")
    last_refreshed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class ArtistGenreModel(Base):
    """V2.5 persisted genre row for one artist.

    A single artist can have one primary row plus several secondary rows. Every
    row stores source summaries and evidence ids as JSON so the frontend and
    later model blocks can explain why a genre chip exists.
    """

    __tablename__ = "artist_genres"
    __table_args__ = (
        UniqueConstraint("artist_slug", "genre", name="uq_artist_genres_artist_genre"),
        Index("ix_artist_genres_artist_primary", "artist_slug", "is_primary"),
        Index("ix_artist_genres_genre_primary", "genre", "is_primary"),
        Index("ix_artist_genres_confidence", "confidence", "confidence_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="CASCADE"), nullable=True, index=True)
    artist_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    genre: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    evidence_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    source_keys_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="inferred")
    needs_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class HistoricalTimetableSlotModel(Base):
    """Normalized historical timetable slot imported in V2.6.

    The row keeps both the observed room alias from the historical timetable and
    the normalized Fabrik room name. This is important because older images use
    names such as New Crystal, Crystal Area, Rave Area Club or Club 360, while
    the model needs one canonical room key per physical room.
    """

    __tablename__ = "historical_timetable_slots"
    __table_args__ = (
        UniqueConstraint(
            "year",
            "event_day",
            "room_slug",
            "start_minutes",
            "artist_slug",
            name="uq_historical_slot_identity",
        ),
        Index("ix_historical_slots_year_day", "year", "event_day"),
        Index("ix_historical_slots_room_time", "year", "event_day", "room_slug", "start_minutes"),
        Index("ix_historical_slots_artist", "artist_slug"),
        Index("ix_historical_slots_headliner", "year", "is_headliner_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_day: Mapped[str] = mapped_column(String(40), nullable=False)
    festival_day: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    date_label: Mapped[str | None] = mapped_column(String(80), nullable=True)

    room_name: Mapped[str] = mapped_column(String(160), nullable=False)
    room_slug: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    observed_room_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    room_aliases_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="SET NULL"), nullable=True)
    artist_slug: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    artist_name: Mapped[str] = mapped_column(String(255), nullable=False)
    show_name: Mapped[str] = mapped_column(String(255), nullable=False)
    performance_type: Mapped[str] = mapped_column(String(80), nullable=False, default="solo")

    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    start_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    slot_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    slot_type: Mapped[str] = mapped_column(String(80), nullable=False, default="standard")
    is_headliner_slot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_closing_slot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_warmup_slot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_special_show: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence_items.id", ondelete="SET NULL"), nullable=True)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    extraction_method: Mapped[str] = mapped_column(String(80), nullable=False, default="manual_image_transcription")
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="pending_review")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class V2ArtistDemandPredictionModel(Base):
    """Persisted V2.7 demand-model output for one artist and edition year.

    The feature and factor JSON columns deliberately duplicate the model input
    snapshot used at generation time. Raw data remains traceable through the
    evidence layer, but storing this compact snapshot makes comparisons between
    model versions reproducible.
    """

    __tablename__ = "v2_artist_demand_predictions"
    __table_args__ = (
        UniqueConstraint("year", "artist_slug", name="uq_v2_artist_demand_year_artist"),
        Index("ix_v2_artist_demand_year_rank", "year", "rank"),
        Index("ix_v2_artist_demand_year_score", "year", "demand_score"),
        Index("ix_v2_artist_demand_genre", "year", "main_genre"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="SET NULL"), nullable=True)
    artist_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    artist_name: Mapped[str] = mapped_column(String(255), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    main_genre: Mapped[str] = mapped_column(String(160), nullable=False, default="Unknown")
    secondary_genres_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    popularity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    career_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    momentum_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    nexus_affinity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    demand_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    crowd_risk: Mapped[str] = mapped_column(String(40), nullable=False, default="low")
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    method: Mapped[str] = mapped_column(String(120), nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    feature_payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    factor_payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    explanation_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class V2ProbableTimetableSlotModel(Base):
    """Predicted non-official 2026 timetable slot produced by V2.8.

    This table intentionally duplicates demand score snapshots and reason
    payloads from generation time. It is a prediction artifact, not an official
    schedule import, so API consumers can always distinguish it from future
    official timetable data.
    """

    __tablename__ = "v2_probable_timetable_slots"
    __table_args__ = (
        UniqueConstraint("year", "artist_slug", name="uq_v2_probable_timetable_year_artist"),
        UniqueConstraint(
            "year",
            "event_day",
            "room_slug",
            "start_minutes",
            name="uq_v2_probable_timetable_room_slot",
        ),
        Index("ix_v2_probable_timetable_year_day", "year", "event_day"),
        Index("ix_v2_probable_timetable_room_time", "year", "event_day", "room_slug", "start_minutes"),
        Index("ix_v2_probable_timetable_rank", "year", "artist_rank"),
        Index("ix_v2_probable_timetable_confidence", "year", "confidence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    timetable_kind: Mapped[str] = mapped_column(String(80), nullable=False, default="probable")
    event_day: Mapped[str] = mapped_column(String(40), nullable=False)
    festival_day: Mapped[int] = mapped_column(Integer, nullable=False)
    date_label: Mapped[str | None] = mapped_column(String(120), nullable=True)

    room_name: Mapped[str] = mapped_column(String(160), nullable=False)
    room_slug: Mapped[str] = mapped_column(String(160), nullable=False)
    room_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="SET NULL"), nullable=True)
    artist_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    artist_name: Mapped[str] = mapped_column(String(255), nullable=False)
    artist_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    show_name: Mapped[str] = mapped_column(String(255), nullable=False)
    performance_type: Mapped[str] = mapped_column(String(80), nullable=False, default="solo")
    main_genre: Mapped[str] = mapped_column(String(160), nullable=False, default="Unknown")
    secondary_genres_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    start_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    slot_order: Mapped[int] = mapped_column(Integer, nullable=False)
    slot_type: Mapped[str] = mapped_column(String(80), nullable=False, default="standard")
    is_headliner_slot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_closing_slot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_warmup_slot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_special_show: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    popularity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    career_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    momentum_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    nexus_affinity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    demand_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_pressure_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    probability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    crowd_risk: Mapped[str] = mapped_column(String(40), nullable=False, default="low")
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")

    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    method: Mapped[str] = mapped_column(String(160), nullable=False)
    official_status: Mapped[str] = mapped_column(String(80), nullable=False, default="predicted_not_official")
    source_status: Mapped[str] = mapped_column(String(80), nullable=False, default="no_official_timetable_yet")
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    reason_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    warning_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    historical_pattern_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class V2OptimizedTimetableSlotModel(Base):
    """Persisted V2.9 optimized timetable slot for one variant.

    V2.9 keeps one row per artist/variant assignment. The probable timetable
    remains available as the "what would the organization probably do" baseline,
    while this table stores three optimization strategies built from the same
    inputs with comparable crowding, conflict and fan-experience metrics.
    """

    __tablename__ = "v2_optimized_timetable_slots"
    __table_args__ = (
        UniqueConstraint("year", "variant_key", "artist_slug", name="uq_v2_optimized_year_variant_artist"),
        UniqueConstraint(
            "year",
            "variant_key",
            "event_day",
            "room_slug",
            "start_minutes",
            name="uq_v2_optimized_variant_room_slot",
        ),
        Index("ix_v2_optimized_year_variant", "year", "variant_key"),
        Index("ix_v2_optimized_room_time", "year", "variant_key", "event_day", "room_slug", "start_minutes"),
        Index("ix_v2_optimized_artist", "artist_slug"),
        Index("ix_v2_optimized_scores", "year", "variant_key", "optimization_score"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    variant_key: Mapped[str] = mapped_column(String(80), nullable=False)
    variant_name: Mapped[str] = mapped_column(String(160), nullable=False)
    variant_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    event_day: Mapped[str] = mapped_column(String(40), nullable=False)
    festival_day: Mapped[int] = mapped_column(Integer, nullable=False)
    date_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    room_name: Mapped[str] = mapped_column(String(160), nullable=False)
    room_slug: Mapped[str] = mapped_column(String(160), nullable=False)
    room_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)

    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="SET NULL"), nullable=True)
    artist_slug: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    artist_name: Mapped[str] = mapped_column(String(255), nullable=False)
    artist_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    show_name: Mapped[str] = mapped_column(String(255), nullable=False)
    performance_type: Mapped[str] = mapped_column(String(80), nullable=False, default="solo")
    main_genre: Mapped[str] = mapped_column(String(160), nullable=False, default="Unknown")
    secondary_genres_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    start_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    slot_order: Mapped[int] = mapped_column(Integer, nullable=False)
    slot_type: Mapped[str] = mapped_column(String(80), nullable=False, default="standard")
    is_headliner_slot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_closing_slot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_warmup_slot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_special_show: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    popularity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    career_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    momentum_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    nexus_affinity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    demand_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    expected_pressure_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    crowding_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    conflict_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    optimization_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    crowd_risk: Mapped[str] = mapped_column(String(40), nullable=False, default="low")

    original_room_slug: Mapped[str | None] = mapped_column(String(160), nullable=True)
    original_start_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    probable_slot_id: Mapped[int | None] = mapped_column(ForeignKey("v2_probable_timetable_slots.id", ondelete="SET NULL"), nullable=True)

    model_version: Mapped[str] = mapped_column(String(120), nullable=False)
    method: Mapped[str] = mapped_column(String(160), nullable=False)
    solver_status: Mapped[str] = mapped_column(String(120), nullable=False, default="heuristic")
    official_status: Mapped[str] = mapped_column(String(80), nullable=False, default="optimized_not_official")
    source_status: Mapped[str] = mapped_column(String(80), nullable=False, default="no_official_timetable_yet")
    is_official: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    reason_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    constraint_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    warning_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EventContractModel(Base):
    """Functional event contract used by V3 data and ML pipelines.

    This table fixes how an edition is represented in time. V3.1 uses it to
    model Nexus 2026 as one continuous 18-hour event instead of two separated
    calendar days. Future ML datasets should read this contract rather than
    inventing their own date/day interpretation.
    """

    __tablename__ = "event_contracts"
    __table_args__ = (
        UniqueConstraint("year", name="uq_event_contracts_year"),
        Index("ix_event_contracts_event_key", "event_key"),
        Index("ix_event_contracts_year_continuous", "year", "continuous_event"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    event_key: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, default="festival")
    venue: Mapped[str] = mapped_column(String(255), nullable=False, default="Fabrik Madrid")
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False, default="Europe/Madrid")

    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    start_label: Mapped[str] = mapped_column(String(40), nullable=False)
    end_label: Mapped[str] = mapped_column(String(40), nullable=False)
    duration_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)

    continuous_event: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    functional_day_key: Mapped[str] = mapped_column(String(80), nullable=False, default="nexus_day")
    visible_label: Mapped[str] = mapped_column(String(160), nullable=False, default="Evento continuo")

    source_status: Mapped[str] = mapped_column(String(80), nullable=False, default="researched_event_contract")
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="high")
    extraction_method: Mapped[str] = mapped_column(String(80), nullable=False, default="manual_researched_contract")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    peak_windows_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EventTimeWindowModel(Base):
    """One continuous time window inside an event contract.

    Windows are stored as minutes from event start, not as independent calendar
    days. This prevents the 2026 event from being split into Friday/Saturday in
    downstream timetable, saturation and ML feature code.
    """

    __tablename__ = "event_time_windows"
    __table_args__ = (
        UniqueConstraint("year", "window_key", name="uq_event_time_windows_year_key"),
        Index("ix_event_time_windows_contract_order", "event_contract_id", "window_index"),
        Index("ix_event_time_windows_year_start", "year", "start_minutes_from_event_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_contract_id: Mapped[int] = mapped_column(ForeignKey("event_contracts.id", ondelete="CASCADE"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    window_index: Mapped[int] = mapped_column(Integer, nullable=False)
    window_key: Mapped[str] = mapped_column(String(120), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)

    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    start_minutes_from_event_start: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minutes_from_event_start: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)

    crosses_midnight: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    functional_day_key: Mapped[str] = mapped_column(String(80), nullable=False, default="nexus_day")
    slot_type: Mapped[str] = mapped_column(String(80), nullable=False, default="standard")
    is_peak_window: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    evidence_status: Mapped[str] = mapped_column(String(80), nullable=False, default="contract_window")
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="high")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class RawSourceModel(Base):
    """V3 ML-ready registry for raw data sources.

    This table is separate from the V2 evidence `sources` table because V3 needs
    ingestion-oriented metadata: access method, legal/ToS risk, ML value, cost,
    and whether a source should be reviewed before its snapshots become model
    features.
    """

    __tablename__ = "raw_sources"
    __table_args__ = (
        UniqueConstraint("source_key", name="uq_raw_sources_source_key"),
        Index("ix_raw_sources_type_confidence", "source_type", "confidence"),
        Index("ix_raw_sources_active_ml_value", "is_active", "ml_value"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    base_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_method: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")
    extraction_method: Mapped[str] = mapped_column(String(80), nullable=False, default="manual")
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    ml_value: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    legal_risk: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")
    cost_level: Mapped[str] = mapped_column(String(40), nullable=False, default="free_or_unknown")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    requires_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class RawSnapshotModel(Base):
    """Raw captured payload from an external/internal source.

    Raw snapshots are the audit trail of V3. They keep the original payload so
    future normalization, entity-resolution and feature-engineering logic can be
    rerun without pretending the data appeared magically inside a model.
    """

    __tablename__ = "raw_snapshots"
    __table_args__ = (
        UniqueConstraint("snapshot_key", name="uq_raw_snapshots_snapshot_key"),
        Index("ix_raw_snapshots_entity", "entity_type", "entity_key"),
        Index("ix_raw_snapshots_source_captured", "source_key", "captured_at"),
        Index("ix_raw_snapshots_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    raw_source_id: Mapped[int | None] = mapped_column(ForeignKey("raw_sources.id", ondelete="SET NULL"), nullable=True, index=True)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    snapshot_key: Mapped[str] = mapped_column(String(255), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="captured")
    schema_version: Mapped[str] = mapped_column(String(80), nullable=False, default="v3.2")
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    normalized_hint_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class NormalizedMetricModel(Base):
    """Metric normalized from raw/evidence payloads into ML-friendly shape."""

    __tablename__ = "normalized_metrics"
    __table_args__ = (
        Index("ix_normalized_metrics_entity_metric", "entity_type", "entity_key", "metric_key"),
        Index("ix_normalized_metrics_source", "source_key", "confidence"),
        Index("ix_normalized_metrics_feature_candidate", "feature_candidate"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    raw_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("raw_snapshots.id", ondelete="SET NULL"), nullable=True, index=True)
    source_key: Mapped[str] = mapped_column(String(160), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(160), nullable=False)
    metric_value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    value_type: Mapped[str] = mapped_column(String(40), nullable=False, default="numeric")
    normalized_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")
    source_method: Mapped[str] = mapped_column(String(80), nullable=False, default="normalized_from_raw")
    feature_candidate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MLDatasetModel(Base):
    """Versioned dataset definition used for training, evaluation or prediction."""

    __tablename__ = "ml_datasets"
    __table_args__ = (
        UniqueConstraint("dataset_key", name="uq_ml_datasets_dataset_key"),
        Index("ix_ml_datasets_target_version", "model_target", "dataset_version"),
        Index("ix_ml_datasets_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_key: Mapped[str] = mapped_column(String(255), nullable=False)
    model_target: Mapped[str] = mapped_column(String(120), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(80), nullable=False)
    dataset_kind: Mapped[str] = mapped_column(String(80), nullable=False, default="training")
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, default="artist")
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feature_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    label_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    split_strategy: Mapped[str] = mapped_column(String(120), nullable=False, default="not_built_yet")
    source_snapshot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="draft")
    is_training_dataset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    feature_schema_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    label_schema_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    filters_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    lineage_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MLFeatureSnapshotModel(Base):
    """Feature vector for one entity within a versioned dataset."""

    __tablename__ = "ml_feature_snapshots"
    __table_args__ = (
        UniqueConstraint("dataset_key", "entity_type", "entity_key", "feature_set_name", "feature_version", name="uq_ml_feature_snapshot_identity"),
        Index("ix_ml_feature_snapshots_dataset", "dataset_id", "feature_set_name"),
        Index("ix_ml_feature_snapshots_entity", "entity_type", "entity_key"),
        Index("ix_ml_feature_snapshots_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("ml_datasets.id", ondelete="SET NULL"), nullable=True, index=True)
    dataset_key: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    feature_set_name: Mapped[str] = mapped_column(String(120), nullable=False)
    feature_version: Mapped[str] = mapped_column(String(80), nullable=False)
    feature_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    feature_columns_json: Mapped[list[object]] = mapped_column(JSON, nullable=False, default=list)
    missing_features_json: Mapped[list[object]] = mapped_column(JSON, nullable=False, default=list)
    source_metric_keys_json: Mapped[list[object]] = mapped_column(JSON, nullable=False, default=list)
    source_snapshot_ids_json: Mapped[list[object]] = mapped_column(JSON, nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    leakage_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MLLabelModel(Base):
    """Versioned target/proxy label used by supervised ML training."""

    __tablename__ = "ml_labels"
    __table_args__ = (
        Index("ix_ml_labels_target_version", "model_target", "label_version"),
        Index("ix_ml_labels_entity", "entity_type", "entity_key"),
        Index("ix_ml_labels_type_confidence", "label_type", "confidence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("ml_datasets.id", ondelete="SET NULL"), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    model_target: Mapped[str] = mapped_column(String(120), nullable=False)
    label_key: Mapped[str] = mapped_column(String(160), nullable=False)
    label_version: Mapped[str] = mapped_column(String(80), nullable=False)
    label_value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    label_value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    label_value_category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_method: Mapped[str] = mapped_column(String(120), nullable=False)
    label_type: Mapped[str] = mapped_column(String(60), nullable=False, default="proxy")
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    evidence_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MLModelRunModel(Base):
    """Training/evaluation run metadata for baselines and real ML models."""

    __tablename__ = "ml_model_runs"
    __table_args__ = (
        UniqueConstraint("run_key", name="uq_ml_model_runs_run_key"),
        Index("ix_ml_model_runs_target_version", "model_target", "model_version"),
        Index("ix_ml_model_runs_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    run_key: Mapped[str] = mapped_column(String(255), nullable=False)
    model_name: Mapped[str] = mapped_column(String(160), nullable=False)
    model_target: Mapped[str] = mapped_column(String(120), nullable=False)
    model_type: Mapped[str] = mapped_column(String(80), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(120), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    dataset_id: Mapped[int | None] = mapped_column(ForeignKey("ml_datasets.id", ondelete="SET NULL"), nullable=True, index=True)
    dataset_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trained: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    training_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    training_finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    training_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    validation_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    feature_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metrics_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    parameters_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    artifact_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MLPredictionModel(Base):
    """Persisted output generated by a model run for an entity/year."""

    __tablename__ = "ml_predictions"
    __table_args__ = (
        UniqueConstraint("run_key", "prediction_key", name="uq_ml_predictions_run_prediction"),
        Index("ix_ml_predictions_target_year", "model_target", "prediction_year"),
        Index("ix_ml_predictions_entity", "entity_type", "entity_key"),
        Index("ix_ml_predictions_final", "is_final", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    model_run_id: Mapped[int | None] = mapped_column(ForeignKey("ml_model_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    feature_snapshot_id: Mapped[int | None] = mapped_column(ForeignKey("ml_feature_snapshots.id", ondelete="SET NULL"), nullable=True, index=True)
    run_key: Mapped[str] = mapped_column(String(255), nullable=False)
    model_target: Mapped[str] = mapped_column(String(120), nullable=False)
    prediction_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_key: Mapped[str] = mapped_column(String(255), nullable=False)
    prediction_key: Mapped[str] = mapped_column(String(255), nullable=False)
    prediction_value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    prediction_value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    prediction_class: Mapped[str | None] = mapped_column(String(120), nullable=True)
    prediction_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    drivers_json: Mapped[list[object]] = mapped_column(JSON, nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="draft")
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ArtistMasterModel(Base):
    """Canonical V3 artist identity used before external profile ingestion.

    This table does not replace the original `artists` seed table immediately.
    It creates an ML-safe identity layer where external profiles, aliases and
    review decisions can point to one canonical artist before any future feature
    builder consumes platform metrics.
    """

    __tablename__ = "artist_master"
    __table_args__ = (
        UniqueConstraint("canonical_artist_key", name="uq_artist_master_key"),
        UniqueConstraint("source_artist_slug", name="uq_artist_master_source_slug"),
        Index("ix_artist_master_normalized_name", "normalized_name"),
        Index("ix_artist_master_review_status", "review_status", "needs_manual_review"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="SET NULL"), nullable=True, index=True)
    canonical_artist_key: Mapped[str] = mapped_column(String(255), nullable=False)
    source_artist_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_genre_seed: Mapped[str | None] = mapped_column(String(160), nullable=True)
    appearance_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_2026_artist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_top_artist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    needs_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    review_status: Mapped[str] = mapped_column(String(60), nullable=False, default="seed_verified")
    feature_eligibility_status: Mapped[str] = mapped_column(String(80), nullable=False, default="internal_seed_only")
    alias_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    appearances_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ArtistAliasModel(Base):
    """Alias/name variant belonging to a canonical artist."""

    __tablename__ = "artist_aliases"
    __table_args__ = (
        UniqueConstraint("artist_master_id", "normalized_alias", "alias_type", name="uq_artist_alias_identity"),
        Index("ix_artist_aliases_normalized", "normalized_alias"),
        Index("ix_artist_aliases_confidence", "confidence", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artist_master_id: Mapped[int] = mapped_column(ForeignKey("artist_master.id", ondelete="CASCADE"), nullable=False, index=True)
    canonical_artist_key: Mapped[str] = mapped_column(String(255), nullable=False)
    alias: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False)
    alias_type: Mapped[str] = mapped_column(String(80), nullable=False, default="display_name")
    source_key: Mapped[str] = mapped_column(String(160), nullable=False, default="nexus_seed")
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="high")
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="active")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ArtistIdentityLinkModel(Base):
    """Reviewed or pending link between a canonical artist and an external profile."""

    __tablename__ = "artist_identity_links"
    __table_args__ = (
        UniqueConstraint("artist_master_id", "platform", "profile_url", name="uq_artist_identity_link_url"),
        UniqueConstraint("artist_master_id", "platform", "external_id", name="uq_artist_identity_link_external_id"),
        Index("ix_artist_identity_links_platform_status", "platform", "match_status"),
        Index("ix_artist_identity_links_feature_eligible", "is_feature_eligible", "confidence"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artist_master_id: Mapped[int] = mapped_column(ForeignKey("artist_master.id", ondelete="CASCADE"), nullable=False, index=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="SET NULL"), nullable=True, index=True)
    canonical_artist_key: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(80), nullable=False)
    profile_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalized_profile_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    match_status: Mapped[str] = mapped_column(String(60), nullable=False, default="pending_review")
    match_method: Mapped[str] = mapped_column(String(120), nullable=False, default="seed_match")
    source_table: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_feature_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_manual_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ArtistIdentityCandidateModel(Base):
    """Candidate external profile that needs verification or rejection."""

    __tablename__ = "artist_identity_candidates"
    __table_args__ = (
        UniqueConstraint("candidate_key", name="uq_artist_identity_candidate_key"),
        Index("ix_artist_identity_candidates_status", "status", "confidence"),
        Index("ix_artist_identity_candidates_artist", "artist_master_id", "status"),
        Index("ix_artist_identity_candidates_platform", "platform", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    artist_master_id: Mapped[int] = mapped_column(ForeignKey("artist_master.id", ondelete="CASCADE"), nullable=False, index=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id", ondelete="SET NULL"), nullable=True)
    canonical_artist_key: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_key: Mapped[str] = mapped_column(String(255), nullable=False)
    platform: Mapped[str] = mapped_column(String(80), nullable=False)
    candidate_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_candidate_name: Mapped[str] = mapped_column(String(255), nullable=False)
    candidate_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    match_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="pending_review")
    suggested_action: Mapped[str] = mapped_column(String(80), nullable=False, default="manual_review")
    match_method: Mapped[str] = mapped_column(String(120), nullable=False, default="name_similarity")
    source_table: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
