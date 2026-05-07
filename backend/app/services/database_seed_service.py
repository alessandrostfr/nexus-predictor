"""Seed the Nexus Predictor database from the researched JSON dataset."""

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import Base, engine, safe_database_url
from app.db.models import ArtistModel, DatasetMetaModel, EditionModel, RoomModel
from app.repositories.json_repository import JsonSeedRepository

json_repository = JsonSeedRepository()


def dumps_json(value: Any) -> str:
    """Serialize JSON consistently for Text columns."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True)



def resolve_count(value: Any, fallback: int = 0) -> int:
    """Resolve count values that may be stored as int or confidence dictionaries."""
    if isinstance(value, int):
        return value
    if isinstance(value, dict):
        for key in ("confirmed", "estimated", "value"):
            candidate = value.get(key)
            if isinstance(candidate, int):
                return candidate
    return fallback

def loads_json(value: str | None, fallback: Any) -> Any:
    """Deserialize Text JSON safely."""
    if value is None:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def create_database_schema() -> None:
    """Create tables only when the compatibility switch is enabled.

    The official V2 path is Alembic migrations. This fallback exists for short
    lived SQLite experiments and keeps the old seed workflow available without
    making `create_all()` the default production behavior.
    """
    if settings.AUTO_CREATE_DATABASE_SCHEMA:
        Base.metadata.create_all(bind=engine)


def get_table_count(db: Session, model: type) -> int:
    """Return the number of rows in a table."""
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def is_database_seeded(db: Session) -> bool:
    """Return whether the main seed tables already contain data."""
    return get_table_count(db, EditionModel) > 0 and get_table_count(db, ArtistModel) > 0


def set_meta_value(db: Session, key: str, value: str) -> None:
    """Insert or update a dataset metadata key."""
    existing = db.scalar(select(DatasetMetaModel).where(DatasetMetaModel.key == key))
    if existing is None:
        db.add(DatasetMetaModel(key=key, value=value))
    else:
        existing.value = value


def get_meta_value(db: Session, key: str) -> str | None:
    """Return a metadata value if present."""
    existing = db.scalar(select(DatasetMetaModel).where(DatasetMetaModel.key == key))
    return existing.value if existing else None


def seed_database_from_json(db: Session, *, reset: bool = False) -> dict[str, int]:
    """Load JSON seed files into the configured database.

    Args:
        db: Active SQLAlchemy session.
        reset: When true, existing rows are deleted first. This is useful after
            editing JSON files in future research passes.

    Returns:
        Inserted row counts by entity type.
    """
    create_database_schema()

    if reset:
        db.query(RoomModel).delete()
        db.query(ArtistModel).delete()
        db.query(EditionModel).delete()
        db.query(DatasetMetaModel).delete()
        db.flush()

    editions = json_repository.list_editions()
    artist_index = json_repository.get_artist_index()
    venue = json_repository.get_venue()

    inserted_editions = 0
    for edition in editions:
        existing = db.scalar(select(EditionModel).where(EditionModel.year == edition.get("year")))
        if existing is not None:
            continue

        db.add(
            EditionModel(
                year=int(edition["year"]),
                name=edition.get("name", f"Nexus Festival {edition['year']}"),
                status=edition.get("status", "unknown"),
                venue=edition.get("venue", "Fabrik Madrid"),
                city=edition.get("city"),
                date_start=edition.get("date_start"),
                date_end=edition.get("date_end"),
                duration_hours=edition.get("duration_hours"),
                artist_count=resolve_count(edition.get("artist_count"), len(edition.get("lineup", []))),
                stage_count=resolve_count(edition.get("stage_count"), len(edition.get("stages", []))),
                attendance_json=dumps_json(edition.get("attendance", {})),
                lineup_json=dumps_json(edition.get("lineup", [])),
                sources_json=dumps_json(edition.get("sources", [])),
                raw_json=dumps_json(edition),
            )
        )
        inserted_editions += 1

    inserted_artists = 0
    for artist in artist_index.get("artists", []):
        existing = db.scalar(select(ArtistModel).where(ArtistModel.slug == artist.get("slug")))
        if existing is not None:
            continue

        db.add(
            ArtistModel(
                slug=artist["slug"],
                name=artist.get("name", artist["slug"]),
                normalized_name=artist.get("normalized_name", artist.get("name", artist["slug"])),
                primary_genre_seed=artist.get("primary_genre_seed", "Unknown"),
                appearance_count=int(artist.get("appearance_count") or len(artist.get("appearances", []))),
                manual_review=bool(artist.get("manual_review", False)),
                data_status=artist.get("data_status", "seed_from_lineup"),
                appearance_years_json=dumps_json(artist.get("appearance_years", [])),
                appearances_json=dumps_json(artist.get("appearances", [])),
                raw_json=dumps_json(artist),
            )
        )
        inserted_artists += 1

    inserted_rooms = 0
    for room in venue.get("rooms", []):
        existing = db.scalar(select(RoomModel).where(RoomModel.name == room.get("name")))
        if existing is not None:
            continue

        db.add(
            RoomModel(
                name=room["name"],
                min_capacity=room.get("min_capacity"),
                estimated_capacity=room.get("estimated_capacity"),
                max_capacity=room.get("max_capacity"),
                confidence=room.get("confidence", "pending"),
                aliases_json=dumps_json(room.get("aliases", [])),
                source_keys_json=dumps_json(room.get("source_keys", [])),
                notes=room.get("notes"),
                raw_json=dumps_json(room),
            )
        )
        inserted_rooms += 1

    set_meta_value(db, "seed_source", "json_files")
    set_meta_value(db, "last_seeded_at", datetime.now(timezone.utc).isoformat())
    db.commit()

    return {
        "editions": inserted_editions,
        "artists": inserted_artists,
        "rooms": inserted_rooms,
    }


def ensure_database_ready(db: Session) -> None:
    """Optionally prepare and seed the database before API reads.

    In the normal V2 PostgreSQL workflow, run `alembic upgrade head` before the
    API starts. If `AUTO_CREATE_DATABASE_SCHEMA=true`, the app can still create
    tables directly for lightweight SQLite checks.
    """
    create_database_schema()
    if settings.AUTO_SEED_DATABASE and not is_database_seeded(db):
        seed_database_from_json(db, reset=False)


def get_database_status(db: Session) -> dict[str, Any]:
    """Return current database seed information."""
    create_database_schema()
    if settings.AUTO_SEED_DATABASE and not is_database_seeded(db):
        seed_database_from_json(db, reset=False)
    editions = get_table_count(db, EditionModel)
    artists = get_table_count(db, ArtistModel)
    rooms = get_table_count(db, RoomModel)

    return {
        "database_url": safe_database_url(),
        "editions": editions,
        "artists": artists,
        "rooms": rooms,
        "seeded": editions > 0 and artists > 0,
        "source": get_meta_value(db, "seed_source") or "not_seeded",
        "last_seeded_at": get_meta_value(db, "last_seeded_at"),
    }
