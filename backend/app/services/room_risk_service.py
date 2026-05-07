"""Room capacity and saturation risk model for Fabrik.

The official Nexus 2026 timetable is still pending, so this service exposes an
honest theoretical simulation. When real slots are added to
backend/app/data/timetables/2026.json, the same API can calculate heatmap values
from official room/time assignments.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.paths import TIMETABLES_DIR, VENUE_DIR
from app.repositories.sqlite_repository import SQLiteRepository
from app.schemas.prediction import ArtistDemandPrediction
from app.schemas.room_risk import (
    RoomCapacityRisk,
    RoomHeatmapCell,
    RoomMapPosition,
    RoomRiskArtist,
    RoomRiskFactor,
    RoomRiskOverview,
    TimetableSlot,
    TimetableStatus,
    VenueSupportArea,
)
from app.services.prediction_service import PredictionService


ROOM_MAP_POSITIONS: dict[str, RoomMapPosition] = {
    "hangar": RoomMapPosition(x=30, y=8, width=23, height=16),
    "open-air": RoomMapPosition(x=8, y=58, width=25, height=19),
    "main-room": RoomMapPosition(x=42, y=51, width=30, height=22),
    "satelite": RoomMapPosition(x=66, y=72, width=18, height=12),
    "crystal-area": RoomMapPosition(x=41, y=38, width=14, height=12),
    "club-area": RoomMapPosition(x=72, y=42, width=13, height=10),
    "area-19": RoomMapPosition(x=80, y=9, width=17, height=15),
    "hotel-fabrik": RoomMapPosition(x=80, y=33, width=12, height=10),
}

ROOM_PULL_MULTIPLIERS: dict[str, float] = {
    # These multipliers are intentionally conservative while there is no
    # official 2026 timetable. The first Block 8 version made too many rooms
    # critical at all times; this version models a more realistic flow where
    # only the strongest room/time combinations become red.
    "main-room": 8.6,
    "open-air": 6.4,
    "hangar": 4.8,
    "satelite": 3.2,
    "club-area": 1.65,
    "crystal-area": 1.95,
    "area-19": 2.75,
}

ROOM_CANDIDATE_LIMITS: dict[str, int] = {
    "main-room": 3,
    "open-air": 4,
    "hangar": 5,
    "satelite": 4,
    "club-area": 5,
    "crystal-area": 4,
    "area-19": 5,
}

DEFAULT_TIME_BANDS = [
    {"key": "18-21", "label": "18:00-21:00 · Entrada / warm-up", "simulation_multiplier": 0.40},
    {"key": "21-00", "label": "21:00-00:00 · Subida", "simulation_multiplier": 0.72},
    {"key": "00-03", "label": "00:00-03:00 · Pico", "simulation_multiplier": 1.32},
    {"key": "03-06", "label": "03:00-06:00 · Cierre", "simulation_multiplier": 0.96},
]


def slugify_room(value: str) -> str:
    """Normalize room names into stable URL slugs."""
    return (
        value.strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("/", "-")
        .replace(" ", "-")
    )


def pressure_level(score: float) -> str:
    """Translate a room pressure score into a readable level.

    Theoretical room pressure is based on the demand model from Block 5 plus
    room fit and hourly flow. Thresholds are intentionally operational: a room
    becomes high risk before it is mathematically full, because crowd movement,
    queues and headliner draw can create pressure before the nominal capacity is
    reached.
    """
    if score >= 92:
        return "critical"
    if score >= 72:
        return "high"
    if score >= 54:
        return "medium"
    if score >= 32:
        return "low"
    return "calm"


def safe_int(value: Any, fallback: int = 0) -> int:
    """Convert values from editable JSON into integers safely."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


class RoomRiskService:
    """Calculate theoretical and timetable-based saturation risk by room."""

    def __init__(self, db: Session) -> None:
        """Create service dependencies using the request database session."""
        self.db = db
        self.repository = SQLiteRepository(db)
        self.prediction_service = PredictionService(db)

    def get_overview(self, year: int = 2026) -> RoomRiskOverview | None:
        """Return complete room risk overview for one edition."""
        if self.repository.get_edition(year) is None:
            return None

        timetable = self.get_timetable_status(year)
        artist_predictions = self._artist_predictions(year)
        rooms = self._build_room_risks(artist_predictions, timetable)
        heatmap = self._build_heatmap(rooms, timetable)

        return RoomRiskOverview(
            year=year,
            venue="Fabrik Madrid",
            generated_at=datetime.now(timezone.utc).isoformat(),
            mode="official_timetable" if timetable.official_available else "theoretical_simulation",
            data_status="simulation_until_official_timetable" if not timetable.official_available else "official_slots_imported",
            official_timetable_available=timetable.official_available,
            rooms=rooms,
            venue_support_areas=self._support_areas(),
            heatmap=heatmap,
            timetable=timetable,
            highest_risk_rooms=sorted(rooms, key=lambda room: room.room_pressure_score, reverse=True)[:3],
            notes=[
                "Room pressure is not an official crowd forecast.",
                "Capacity values are editable estimates and depend on event configuration.",
                "The hotel is shown for orientation only and is excluded from room risk calculations.",
            ],
        )

    def list_rooms(self, year: int = 2026) -> list[RoomCapacityRisk] | None:
        """Return only room risk cards for one edition."""
        overview = self.get_overview(year)
        return overview.rooms if overview else None

    def get_room(self, year: int, room_slug: str) -> RoomCapacityRisk | None:
        """Return one room by slug."""
        rooms = self.list_rooms(year)
        if rooms is None:
            return None
        normalized = slugify_room(room_slug)
        for room in rooms:
            if room.slug == normalized:
                return room
        return None

    def get_timetable_status(self, year: int = 2026) -> TimetableStatus:
        """Read timetable JSON and expose the import contract."""
        payload = self._read_json(TIMETABLES_DIR / f"{year}.json", fallback={})
        slots = [self._slot_from_payload(slot) for slot in payload.get("slots", [])]
        official_available = bool(payload.get("official_available", False) and slots)

        return TimetableStatus(
            year=year,
            official_available=official_available,
            source_status=payload.get("source_status", "no_timetable_file"),
            slots=slots,
            import_contract=payload.get(
                "import_contract",
                {
                    "room_slug": "main-room",
                    "room_name": "Main Room",
                    "start_time": "00:00",
                    "end_time": "01:00",
                    "artist_slugs": ["artist-slug"],
                    "artist_names": ["Artist Name"],
                    "source_status": "official|estimated|manual_draft",
                },
            ),
            notes=payload.get(
                "notes",
                ["No timetable file was found, so the API is returning simulation-ready defaults."],
            ),
        )

    def _read_json(self, path: Path, *, fallback: dict[str, Any]) -> dict[str, Any]:
        """Read editable JSON without breaking the API when a file is missing."""
        if not path.exists():
            return fallback
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _venue_payload(self) -> dict[str, Any]:
        """Load Block 8 venue seed data from JSON first, then SQLite fallback."""
        payload = self._read_json(VENUE_DIR / "fabrik_rooms.json", fallback={})
        if payload.get("rooms"):
            return payload
        return self.repository.get_venue()

    def _artist_predictions(self, year: int) -> list[ArtistDemandPrediction]:
        """Load all artist predictions for the year."""
        ranking = self.prediction_service.list_artist_predictions(year, limit=500)
        return ranking.items if ranking else []

    def _build_room_risks(
        self,
        artist_predictions: list[ArtistDemandPrediction],
        timetable: TimetableStatus,
    ) -> list[RoomCapacityRisk]:
        """Build capacity and pressure cards for every music room."""
        venue = self._venue_payload()
        room_payloads = venue.get("rooms", [])
        rooms: list[RoomCapacityRisk] = []

        for room in room_payloads:
            slug = room.get("slug") or slugify_room(room.get("name", "room"))
            capacity = safe_int(room.get("estimated_capacity"), fallback=1000)
            candidates = self._candidate_artists(room, artist_predictions)
            candidate_limit = ROOM_CANDIDATE_LIMITS.get(slug, 4)
            top_candidates = candidates[:candidate_limit]
            pull_multiplier = ROOM_PULL_MULTIPLIERS.get(slug, 2.0)
            # Conservative baseline flow. A room should not be red just because
            # it exists in the festival: the score must come from room fit,
            # artist demand and selected time band.
            baseline_flow = capacity * 0.12
            demand_sum = sum(artist.demand_score for artist in top_candidates)
            room_density_modifier = self._room_density_modifier(slug)
            draw_units = demand_sum * pull_multiplier * room_density_modifier
            simulated_peak = int(round(baseline_flow + draw_units))
            score = round(min(100.0, (simulated_peak / max(capacity, 1)) * 100), 2)
            percentage = round((simulated_peak / max(capacity, 1)) * 100, 2)

            if timetable.official_available:
                score, percentage, simulated_peak = self._official_slot_pressure(slug, capacity, artist_predictions, timetable)

            rooms.append(
                RoomCapacityRisk(
                    slug=slug,
                    name=room.get("name", slug),
                    area_type=room.get("area_type", "indoor"),
                    is_room=True,
                    min_capacity=room.get("min_capacity"),
                    estimated_capacity=room.get("estimated_capacity"),
                    max_capacity=room.get("max_capacity"),
                    capacity_confidence=room.get("confidence", "estimated"),
                    data_status="official_timetable" if timetable.official_available else "theoretical_simulation",
                    source_status="official_slots_imported" if timetable.official_available else "capacity_seed_plus_artist_demand",
                    room_pressure_score=score,
                    pressure_level=pressure_level(score),
                    pressure_percentage=percentage,
                    simulated_expected_peak=simulated_peak,
                    candidate_genres=room.get("candidate_genres", []),
                    suggested_use=self._suggested_use(slug, score),
                    top_candidate_artists=[self._artist_to_room_risk_artist(artist) for artist in top_candidates],
                    factors=[
                        RoomRiskFactor(
                            key="estimated_capacity",
                            label="Estimated capacity",
                            value=capacity,
                            explanation="Editable room capacity estimate used as the denominator of pressure.",
                        ),
                        RoomRiskFactor(
                            key="candidate_artist_demand",
                            label="Candidate artist demand",
                            value=round(demand_sum, 2),
                            explanation="Sum of top candidate artists that fit this room by genre and demand.",
                        ),
                        RoomRiskFactor(
                            key="room_density_modifier",
                            label="Room density modifier",
                            value=room_density_modifier,
                            explanation="Small rooms and open-air areas are normalized so the whole venue is not red all night in the theoretical mode.",
                        ),
                        RoomRiskFactor(
                            key="timetable_status",
                            label="Timetable status",
                            value=timetable.source_status,
                            explanation="Without official room/time assignments, the score remains a theoretical simulation.",
                        ),
                    ],
                    map_position=ROOM_MAP_POSITIONS.get(slug, RoomMapPosition(x=10, y=10, width=12, height=10)),
                    notes=[
                        room.get("notes") or "Room seed loaded from editable venue JSON.",
                        "Recalculate after importing official timetable slots." if not timetable.official_available else "Calculated from imported timetable slots.",
                    ],
                )
            )

        return sorted(rooms, key=lambda room: room.room_pressure_score, reverse=True)

    def _candidate_artists(
        self,
        room: dict[str, Any],
        artist_predictions: list[ArtistDemandPrediction],
    ) -> list[ArtistDemandPrediction]:
        """Select artists that could plausibly create pressure in a room."""
        slug = room.get("slug") or slugify_room(room.get("name", "room"))
        candidate_genres = {genre.lower() for genre in room.get("candidate_genres", [])}
        selected: list[ArtistDemandPrediction] = []

        for artist in artist_predictions:
            genre_match = artist.main_genre.lower() in candidate_genres
            headliner_fit = slug in {"main-room", "open-air"} and artist.demand_score >= 84
            hangar_fit = slug == "hangar" and artist.main_genre in {"Hardcore", "Uptempo Hardcore", "Industrial Hardcore", "Frenchcore"} and artist.demand_score >= 70
            secondary_fit = slug in {"satelite", "area-19"} and artist.demand_score >= 72 and artist.main_genre != "MC / Host"
            niche_fit = slug in {"club-area", "crystal-area"} and genre_match and artist.demand_score <= 78
            if genre_match or headliner_fit or hangar_fit or secondary_fit or niche_fit:
                selected.append(artist)

        return sorted(selected, key=lambda artist: artist.demand_score, reverse=True)


    def _room_density_modifier(self, slug: str) -> float:
        """Normalize theoretical demand so not every room is saturated all night."""
        modifiers = {
            "main-room": 1.0,
            "open-air": 0.92,
            "hangar": 0.86,
            "satelite": 0.78,
            "club-area": 0.68,
            "crystal-area": 0.66,
            "area-19": 0.76,
        }
        return modifiers.get(slug, 0.75)

    def _time_band_room_curve(self, slug: str, band_key: str) -> float:
        """Give each room a different theoretical hourly curve before official timetable.

        The curve uses the artist-demand ranking as the base signal and then
        distributes pressure through the night: Open Air tends to peak earlier,
        Main Room and Hangar peak around the central hours, and Area 19/Hangar
        stay stronger in the closing window. This avoids a flat map while the
        official timetable is still missing.
        """
        curves = {
            "18-21": {
                "open-air": 1.16,
                "crystal-area": 1.08,
                "club-area": 1.04,
                "main-room": 0.74,
                "hangar": 0.66,
                "satelite": 0.72,
                "area-19": 0.78,
            },
            "21-00": {
                "open-air": 1.20,
                "main-room": 0.96,
                "hangar": 0.92,
                "satelite": 0.84,
                "area-19": 1.05,
                "crystal-area": 0.92,
                "club-area": 0.82,
            },
            "00-03": {
                "main-room": 1.18,
                "hangar": 1.18,
                "satelite": 1.06,
                "open-air": 0.90,
                "area-19": 1.04,
                "crystal-area": 0.96,
                "club-area": 0.86,
            },
            "03-06": {
                "hangar": 1.20,
                "area-19": 1.16,
                "satelite": 0.92,
                "main-room": 0.82,
                "open-air": 0.72,
                "crystal-area": 0.82,
                "club-area": 0.76,
            },
        }
        return curves.get(band_key, {}).get(slug, 1.0)

    def _official_slot_pressure(
        self,
        room_slug: str,
        capacity: int,
        artist_predictions: list[ArtistDemandPrediction],
        timetable: TimetableStatus,
    ) -> tuple[float, float, int]:
        """Calculate pressure from official timetable slots when available."""
        predictions_by_slug = {artist.slug: artist for artist in artist_predictions}
        peak = 0
        for slot in timetable.slots:
            if slot.room_slug != room_slug:
                continue
            slot_score = sum(predictions_by_slug.get(slug).demand_score for slug in slot.artist_slugs if slug in predictions_by_slug)
            slot_peak = int(round(capacity * 0.18 + slot_score * ROOM_PULL_MULTIPLIERS.get(room_slug, 2.0)))
            peak = max(peak, slot_peak)
        percentage = round((peak / max(capacity, 1)) * 100, 2)
        score = round(min(100.0, percentage), 2)
        return score, percentage, peak

    def _build_heatmap(self, rooms: list[RoomCapacityRisk], timetable: TimetableStatus) -> list[RoomHeatmapCell]:
        """Return theoretical or official heatmap cells."""
        cells: list[RoomHeatmapCell] = []
        payload = self._read_json(TIMETABLES_DIR / f"{timetable.year}.json", fallback={})
        time_bands = payload.get("time_bands", DEFAULT_TIME_BANDS)

        for room in rooms:
            for band in time_bands:
                multiplier = float(band.get("simulation_multiplier", 1.0))
                # Small deterministic variation avoids every room following the
                # exact same curve. It keeps the map useful before official slots.
                room_curve = self._time_band_room_curve(room.slug, band.get("key", ""))
                score = round(min(100.0, room.room_pressure_score * multiplier * room_curve), 2)
                cells.append(
                    RoomHeatmapCell(
                        room_slug=room.slug,
                        room_name=room.name,
                        time_band=band.get("key", band.get("label", "unknown")),
                        label=band.get("label", band.get("key", "Unknown band")),
                        score=score,
                        pressure_level=pressure_level(score),
                        data_status="official_timetable" if timetable.official_available else "theoretical_simulation",
                    )
                )
        return cells

    def _support_areas(self) -> list[VenueSupportArea]:
        """Return map-only venue support areas like the hotel."""
        venue = self._venue_payload()
        areas = venue.get("venue_support_areas", []) or [
            {"slug": "hotel-fabrik", "name": "Hotel Fabrik", "area_type": "hotel", "notes": "Orientation only."}
        ]
        return [
            VenueSupportArea(
                slug=area.get("slug", slugify_room(area.get("name", "support"))),
                name=area.get("name", "Support area"),
                area_type=area.get("area_type", "support"),
                is_room=False,
                map_position=ROOM_MAP_POSITIONS.get(area.get("slug", "hotel-fabrik"), ROOM_MAP_POSITIONS["hotel-fabrik"]),
                notes=area.get("notes", "Shown only for orientation."),
            )
            for area in areas
        ]

    def _slot_from_payload(self, slot: dict[str, Any]) -> TimetableSlot:
        """Convert raw timetable JSON to schema."""
        return TimetableSlot(
            room_slug=slugify_room(slot.get("room_slug") or slot.get("room_name") or "unknown-room"),
            room_name=slot.get("room_name") or slot.get("room_slug") or "Unknown room",
            start_time=slot.get("start_time", "00:00"),
            end_time=slot.get("end_time", "00:00"),
            artist_slugs=slot.get("artist_slugs", []),
            artist_names=slot.get("artist_names", []),
            source_status=slot.get("source_status", "official_pending"),
        )

    def _artist_to_room_risk_artist(self, artist: ArtistDemandPrediction) -> RoomRiskArtist:
        """Convert artist prediction into compact room risk artist."""
        return RoomRiskArtist(
            slug=artist.slug,
            name=artist.name,
            main_genre=artist.main_genre,
            demand_score=artist.demand_score,
            crowd_risk=artist.crowd_risk,
            rank=artist.rank,
        )

    def _suggested_use(self, slug: str, score: float) -> str:
        """Give a short operational hint for the room."""
        if score >= 92:
            return "Evitar solapes fuertes: esta sala podría saturarse con headliners o shows especiales."
        if score >= 78:
            return "Programar con cuidado y separar de otros picos de demanda."
        if slug in {"club-area", "crystal-area"}:
            return "Ideal para sets de nicho, locales o sesiones con flujo más controlado."
        return "Riesgo razonable en simulación, revisar al importar horarios oficiales."
