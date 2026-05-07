"""SQLAlchemy models for Nexus Predictor.

The original V1 tables keep the API compatible with the MVP endpoints while V2
adds a real evidence layer. The V2 layer is deliberately explicit: every metric
that may influence popularity, trajectory, genre confidence or timetable models
can be traced back to a source, URL, capture date, confidence level and notes.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
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
