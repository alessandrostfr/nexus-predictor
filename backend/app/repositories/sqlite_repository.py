"""SQLite read repository used by API endpoints."""

from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ArtistModel, EditionModel, RoomModel
from app.services.database_seed_service import ensure_database_ready, loads_json


class SQLiteRepository:
    """High-level read helpers for the local SQLite database."""

    def __init__(self, db: Session) -> None:
        """Store the request-scoped SQLAlchemy session."""
        self.db = db
        ensure_database_ready(self.db)

    def list_editions(self) -> list[dict[str, Any]]:
        """Return compact edition summaries sorted by year."""
        editions = self.db.scalars(select(EditionModel).order_by(EditionModel.year)).all()
        return [self._edition_summary(edition) for edition in editions]

    def get_edition(self, year: int) -> dict[str, Any] | None:
        """Return one detailed edition or `None`."""
        edition = self.db.scalar(select(EditionModel).where(EditionModel.year == year))
        return self._edition_detail(edition) if edition else None

    def get_edition_lineup(self, year: int) -> list[dict[str, Any]] | None:
        """Return the normalized lineup for one edition."""
        edition = self.db.scalar(select(EditionModel).where(EditionModel.year == year))
        if edition is None:
            return None
        return loads_json(edition.lineup_json, [])

    def list_artists(
        self,
        *,
        year: int | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Return artists with optional year and text filters."""
        artists = list(self.db.scalars(select(ArtistModel).order_by(ArtistModel.name)).all())
        filtered = []
        normalized_query = query.lower().strip() if query else None

        for artist in artists:
            summary = self._artist_detail(artist)
            if year is not None and year not in summary["appearance_years"]:
                continue
            if normalized_query and normalized_query not in summary["name"].lower():
                continue
            filtered.append(summary)

        return {
            "total": len(filtered),
            "limit": limit,
            "offset": offset,
            "items": filtered[offset : offset + limit],
        }

    def get_artist(self, slug: str) -> dict[str, Any] | None:
        """Return one artist by slug."""
        artist = self.db.scalar(select(ArtistModel).where(ArtistModel.slug == slug))
        return self._artist_detail(artist) if artist else None

    def get_venue(self) -> dict[str, Any]:
        """Return Fabrik venue data reconstructed from SQLite rooms."""
        rooms = self.list_rooms()
        capacities = [room["estimated_capacity"] for room in rooms if room.get("estimated_capacity")]
        total_estimated_open_capacity = sum(capacities)

        return {
            "venue": "Fabrik Madrid",
            "status": "sqlite_seed",
            "address": "Av. de la Industria, 82, 28970 Humanes de Madrid, Madrid, Spain",
            "capacity_summary": {
                "confirmed_exact_total": None,
                "public_capacity_range_low": min(capacities) if capacities else None,
                "public_capacity_range_mid": total_estimated_open_capacity,
                "public_capacity_range_high": sum(
                    room["max_capacity"] or 0 for room in rooms if room.get("max_capacity")
                ),
                "confidence": "medium",
                "notes": "Capacity remains configuration-dependent and comes from Block 1 researched seeds.",
            },
            "rooms": rooms,
            "sources": [],
        }

    def list_rooms(self) -> list[dict[str, Any]]:
        """Return Fabrik rooms sorted by estimated capacity descending."""
        rooms = self.db.scalars(select(RoomModel).order_by(RoomModel.estimated_capacity.desc())).all()
        return [self._room_detail(room) for room in rooms]

    def list_genres(self) -> list[dict[str, Any]]:
        """Return current genre seed counts across all artists."""
        counter: Counter[str] = Counter()
        artists = self.db.scalars(select(ArtistModel)).all()
        for artist in artists:
            counter[artist.primary_genre_seed or "Unknown"] += 1

        return [
            {"name": name, "artist_count": count}
            for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        ]

    def get_edition_genres(self, year: int) -> dict[str, Any] | None:
        """Return genre seed distribution for artists appearing in one edition."""
        lineup = self.get_edition_lineup(year)
        if lineup is None:
            return None

        slugs_by_name = {artist["name"].lower(): artist for artist in self.list_artists(limit=10000)["items"]}
        counter: Counter[str] = Counter()
        for performance in lineup:
            for artist_name in performance.get("artists", []):
                artist = slugs_by_name.get(str(artist_name).lower())
                counter[artist["primary_genre_seed"] if artist else "Unknown"] += 1

        return {
            "year": year,
            "distribution": [
                {"name": name, "artist_count": count}
                for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
            ],
        }

    def _edition_summary(self, edition: EditionModel) -> dict[str, Any]:
        """Convert an edition row into a compact dictionary."""
        return {
            "year": edition.year,
            "name": edition.name,
            "status": edition.status,
            "venue": edition.venue,
            "date_start": edition.date_start,
            "date_end": edition.date_end,
            "artist_count": edition.artist_count,
            "stage_count": edition.stage_count,
        }

    def _edition_detail(self, edition: EditionModel) -> dict[str, Any]:
        """Convert an edition row into a detailed dictionary."""
        summary = self._edition_summary(edition)
        raw = loads_json(edition.raw_json, {})
        return {
            **summary,
            "city": edition.city,
            "duration_hours": edition.duration_hours,
            "attendance": loads_json(edition.attendance_json, {}),
            "lineup": loads_json(edition.lineup_json, []),
            "sources": loads_json(edition.sources_json, []),
            "raw": raw,
        }

    def _artist_detail(self, artist: ArtistModel) -> dict[str, Any]:
        """Convert an artist row into an API dictionary."""
        raw = loads_json(artist.raw_json, {})
        return {
            "slug": artist.slug,
            "name": artist.name,
            "normalized_name": artist.normalized_name,
            "primary_genre_seed": artist.primary_genre_seed,
            "appearance_count": artist.appearance_count,
            "appearance_years": loads_json(artist.appearance_years_json, []),
            "appearances": loads_json(artist.appearances_json, []),
            "manual_review": artist.manual_review,
            "data_status": artist.data_status,
            "raw": raw,
        }

    def _room_detail(self, room: RoomModel) -> dict[str, Any]:
        """Convert a room row into an API dictionary."""
        raw = loads_json(room.raw_json, {})
        return {
            "name": room.name,
            "aliases": loads_json(room.aliases_json, []),
            "min_capacity": room.min_capacity,
            "estimated_capacity": room.estimated_capacity,
            "max_capacity": room.max_capacity,
            "confidence": room.confidence,
            "source_keys": loads_json(room.source_keys_json, []),
            "notes": room.notes,
            "raw": raw,
        }
