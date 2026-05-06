"""SQLAlchemy models for the local Nexus Predictor database.

Block 2 persists the researched JSON seed into SQLite without losing the raw
source payloads. Later blocks can add richer relational fields, but these models
already let the API read from a real database instead of directly from files.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
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
