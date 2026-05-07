"""V2.8 probable 2026 timetable prediction service.

This block predicts a plausible room/time assignment for Nexus 2026 by combining
three already-closed V2 layers:

- V2.6 historical timetable patterns.
- V2.7 demand/popularity scores.
- V2.5 multi-genre context.

It deliberately does not optimize the timetable. V2.9 will generate optimized
variants. V2.8 only answers: "what would the organization probably do?" while
making it explicit that the result is not official.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    ArtistGenreModel,
    ArtistModel,
    HistoricalTimetableSlotModel,
    RoomModel,
    V2ArtistDemandPredictionModel,
    V2ProbableTimetableSlotModel,
)
from app.repositories.sqlite_repository import SQLiteRepository
from app.schemas.probable_timetable import (
    ProbableTimetableCoverage,
    ProbableTimetableDaySummary,
    ProbableTimetableIntegrityReport,
    ProbableTimetableOverlapIssue,
    ProbableTimetableReason,
    ProbableTimetableRebuildResult,
    ProbableTimetableRoomSummary,
    ProbableTimetableSlotList,
    ProbableTimetableSlotRecord,
    ProbableTimetableYearOverview,
)
from app.services.database_seed_service import dumps_json, ensure_database_ready, loads_json
from app.services.demand_model_service import DemandModelService
from app.services.historical_timetable_service import HistoricalTimetableService
from app.services.scoring_service import normalize_score

MODEL_VERSION = "v2.8-probable-timetable-model"
MODEL_METHOD = "historical_pattern_demand_room_assignment"
OFFICIAL_STATUS = "predicted_not_official"
SOURCE_STATUS = "no_official_timetable_yet"

ROOM_ORDER = ["main-room", "open-air", "hangar", "area-19", "satelite", "club-area", "crystal-area"]
ROOM_NAMES = {
    "main-room": "Main Room",
    "open-air": "Open Air",
    "hangar": "Hangar",
    "area-19": "Area 19",
    "satelite": "Satelite",
    "club-area": "Club Area",
    "crystal-area": "Crystal Area",
}
DEFAULT_ROOM_CAPACITY = {
    "main-room": 4000,
    "open-air": 2600,
    "hangar": 2000,
    "area-19": 1400,
    "satelite": 1300,
    "club-area": 800,
    "crystal-area": 750,
}

# V2.8 keeps a realistic, conservative shell based on the 2025 seven-room model.
# It leaves some unused theoretical capacity because the 2026 lineup currently
# has fewer unique artists than the full 2025 two-day timetable.
ROOM_DAY_PLAN: dict[str, dict[str, dict[str, int]]] = {
    "friday": {
        "main-room": {"start": 21, "slots": 10},
        "open-air": {"start": 21, "slots": 8},
        "hangar": {"start": 21, "slots": 8},
        "area-19": {"start": 21, "slots": 6},
        "satelite": {"start": 21, "slots": 5},
        "club-area": {"start": 21, "slots": 5},
        "crystal-area": {"start": 21, "slots": 5},
    },
    "saturday": {
        "main-room": {"start": 21, "slots": 10},
        "open-air": {"start": 21, "slots": 8},
        "hangar": {"start": 21, "slots": 8},
        "area-19": {"start": 21, "slots": 6},
        "satelite": {"start": 21, "slots": 5},
        "club-area": {"start": 21, "slots": 5},
        "crystal-area": {"start": 21, "slots": 5},
    },
}

GENRE_ROOM_PRIORS: dict[str, dict[str, float]] = {
    "Classic / Legacy Hardstyle": {"main-room": 100, "open-air": 84, "satelite": 72, "hangar": 58},
    "Euphoric Hardstyle": {"main-room": 82, "open-air": 92, "satelite": 78, "hangar": 56},
    "Mainstage Hard Dance": {"main-room": 90, "open-air": 86, "satelite": 66, "hangar": 62},
    "Rawstyle": {"main-room": 84, "open-air": 82, "hangar": 76, "area-19": 72},
    "Xtra Raw": {"hangar": 88, "area-19": 84, "open-air": 74, "main-room": 70},
    "Hardcore": {"hangar": 92, "main-room": 78, "area-19": 70, "club-area": 64},
    "Uptempo Hardcore": {"area-19": 90, "hangar": 84, "club-area": 76, "crystal-area": 62},
    "Frenchcore": {"hangar": 88, "satelite": 78, "main-room": 70, "open-air": 64},
    "Industrial Hardcore": {"hangar": 86, "club-area": 78, "area-19": 72, "crystal-area": 68},
    "Happy Hardcore": {"satelite": 88, "open-air": 76, "main-room": 70, "crystal-area": 60},
    "Freestyle / Hard Dance": {"satelite": 82, "open-air": 72, "club-area": 66, "main-room": 60},
    "Unknown": {"crystal-area": 74, "club-area": 70, "satelite": 64, "area-19": 60},
}

TIME_MULTIPLIERS_BY_POSITION = {
    "warm_up": 0.55,
    "standard": 0.82,
    "headliner": 1.10,
    "closing": 0.96,
}

CONFIDENCE_SCORES = {
    "high": 90.0,
    "medium_high": 78.0,
    "medium": 62.0,
    "low": 42.0,
}


@dataclass
class CandidateAssignment:
    """Temporary room/day assignment before exact slot ordering."""

    prediction: V2ArtistDemandPredictionModel
    day: str
    room_slug: str
    room_score: float
    historical_pattern: dict[str, Any]
    reasons: list[ProbableTimetableReason] = field(default_factory=list)


class ProbableTimetableService:
    """Build and expose the V2.8 probable Nexus 2026 timetable."""

    def __init__(self, db: Session) -> None:
        """Use one request-scoped database session and make V1 seeds available."""
        self.db = db
        ensure_database_ready(self.db)
        self.repository = SQLiteRepository(db)

    def rebuild(self, year: int = 2026, *, reset: bool = True) -> ProbableTimetableRebuildResult:
        """Generate and persist the probable 2026 timetable."""
        if self.repository.get_edition(year) is None:
            raise ValueError(f"Edition {year} was not found.")

        self._ensure_inputs(year)
        generated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        if reset:
            self.db.execute(delete(V2ProbableTimetableSlotModel).where(V2ProbableTimetableSlotModel.year == year))
            self.db.commit()

        predictions = self._demand_predictions(year)
        room_inventory = self._room_inventory()
        historical_patterns = self._historical_patterns()
        assignments, warnings = self._assign_rooms_and_days(predictions, historical_patterns)
        slots = self._materialize_slots(assignments, room_inventory=room_inventory, generated_at=generated_at, year=year)

        for slot in slots:
            existing = self.db.scalar(
                select(V2ProbableTimetableSlotModel).where(
                    V2ProbableTimetableSlotModel.year == year,
                    V2ProbableTimetableSlotModel.artist_slug == slot.artist_slug,
                )
            )
            if existing is not None:
                slot.id = existing.id
                slot.created_at = existing.created_at
            self.db.merge(slot)

        self.db.commit()
        rooms_used = len({slot.room_slug for slot in slots})
        return ProbableTimetableRebuildResult(
            year=year,
            model_version=MODEL_VERSION,
            method=MODEL_METHOD,
            slots=len(slots),
            assigned_artists=len(slots),
            unassigned_artists=max(0, len(predictions) - len(slots)),
            rooms_used=rooms_used,
            official_available=False,
            source_status=SOURCE_STATUS,
            generated_at=generated_at.replace(tzinfo=timezone.utc).isoformat(),
            warnings=warnings,
        )

    def coverage(self, year: int = 2026) -> ProbableTimetableCoverage | None:
        """Return V2.8 coverage counters."""
        if self.repository.get_edition(year) is None:
            return None
        self._ensure_probable_timetable(year)
        rows = self._all_slots(year)
        predictions = self._demand_predictions(year)
        confidence_counts = Counter(row.confidence for row in rows)
        slots_by_day = Counter(row.event_day for row in rows)
        slots_by_room = Counter(row.room_name for row in rows)
        generated_at = max((row.generated_at for row in rows if row.generated_at), default=None)
        average_probability = round(sum(row.probability_score for row in rows) / len(rows), 2) if rows else 0.0
        average_confidence = round(sum(CONFIDENCE_SCORES.get(row.confidence, 50.0) for row in rows) / len(rows), 2) if rows else 0.0
        return ProbableTimetableCoverage(
            year=year,
            timetable_kind="probable",
            official_available=False,
            source_status=SOURCE_STATUS,
            total_slots=len(rows),
            total_artists=len(predictions),
            assigned_artists=len(rows),
            unassigned_artists=max(0, len(predictions) - len(rows)),
            total_days=len({row.event_day for row in rows}),
            total_rooms=len({row.room_slug for row in rows}),
            rooms=sorted({row.room_name for row in rows}),
            slots_by_day={key: slots_by_day[key] for key in sorted(slots_by_day)},
            slots_by_room={key: slots_by_room[key] for key in sorted(slots_by_room)},
            headliner_slots=sum(1 for row in rows if row.is_headliner_slot),
            warmup_slots=sum(1 for row in rows if row.is_warmup_slot),
            closing_slots=sum(1 for row in rows if row.is_closing_slot),
            average_probability_score=average_probability,
            average_confidence_score=average_confidence,
            confidence_breakdown={key: confidence_counts[key] for key in sorted(confidence_counts)},
            model_version=MODEL_VERSION,
            method=MODEL_METHOD,
            generated_at=generated_at.replace(tzinfo=timezone.utc).isoformat() if generated_at else None,
        )

    def year_overview(self, year: int = 2026) -> ProbableTimetableYearOverview | None:
        """Return a full timetable overview with room/day summaries."""
        if self.repository.get_edition(year) is None:
            return None
        self._ensure_probable_timetable(year)
        rows = self._all_slots(year)
        confidence_counts = Counter(row.confidence for row in rows)
        return ProbableTimetableYearOverview(
            year=year,
            timetable_kind="probable",
            official_available=False,
            official_status=OFFICIAL_STATUS,
            source_status=SOURCE_STATUS,
            slot_count=len(rows),
            artist_count=len({row.artist_slug for row in rows}),
            room_count=len({row.room_slug for row in rows}),
            rooms=self.rooms_for_year(year),
            days=self._day_summaries(rows),
            headliner_slots=sum(1 for row in rows if row.is_headliner_slot),
            warmup_slots=sum(1 for row in rows if row.is_warmup_slot),
            closing_slots=sum(1 for row in rows if row.is_closing_slot),
            confidence_breakdown={key: confidence_counts[key] for key in sorted(confidence_counts)},
            notes=[
                "This is a predicted timetable, not an official Nexus/Fabrik schedule.",
                "Room and time assignments are inferred from 2022-2025 timetable patterns and V2.7 demand scores.",
                "V2.9 will generate optimized alternatives; V2.8 models the most probable organization behavior.",
            ],
        )

    def list_slots(
        self,
        *,
        year: int = 2026,
        event_day: str | None = None,
        room: str | None = None,
        artist_slug: str | None = None,
        only_headliners: bool = False,
        limit: int = 200,
        offset: int = 0,
    ) -> ProbableTimetableSlotList | None:
        """Return predicted slots with common filters."""
        if self.repository.get_edition(year) is None:
            return None
        self._ensure_probable_timetable(year)
        statement = select(V2ProbableTimetableSlotModel).where(V2ProbableTimetableSlotModel.year == year)
        if event_day:
            statement = statement.where(func.lower(V2ProbableTimetableSlotModel.event_day) == event_day.lower())
        if room:
            room_slug = self._normalize_room_filter(room)
            statement = statement.where(V2ProbableTimetableSlotModel.room_slug == room_slug)
        if artist_slug:
            statement = statement.where(V2ProbableTimetableSlotModel.artist_slug == artist_slug)
        if only_headliners:
            statement = statement.where(V2ProbableTimetableSlotModel.is_headliner_slot.is_(True))

        ordered = statement.order_by(
            V2ProbableTimetableSlotModel.event_day.asc(),
            V2ProbableTimetableSlotModel.room_slug.asc(),
            V2ProbableTimetableSlotModel.start_minutes.asc(),
        )
        rows = list(self.db.scalars(ordered).all())
        return ProbableTimetableSlotList(
            year=year,
            total=len(rows),
            limit=limit,
            offset=offset,
            items=[self._row_to_slot(row) for row in rows[offset : offset + limit]],
        )

    def get_artist_slot(self, year: int, artist_slug: str) -> ProbableTimetableSlotRecord | None:
        """Return the predicted slot for one artist."""
        self._ensure_probable_timetable(year)
        row = self.db.scalar(
            select(V2ProbableTimetableSlotModel).where(
                V2ProbableTimetableSlotModel.year == year,
                V2ProbableTimetableSlotModel.artist_slug == artist_slug,
            )
        )
        return self._row_to_slot(row) if row else None

    def rooms_for_year(self, year: int = 2026, *, event_day: str | None = None) -> list[ProbableTimetableRoomSummary]:
        """Return predicted room summaries."""
        self._ensure_probable_timetable(year)
        rows = self._all_slots(year)
        if event_day:
            rows = [row for row in rows if row.event_day == event_day]

        grouped: dict[tuple[str | None, str], list[V2ProbableTimetableSlotModel]] = defaultdict(list)
        for row in rows:
            grouped[(row.event_day if event_day else None, row.room_slug)].append(row)

        summaries = []
        for (day, room_slug), items in sorted(grouped.items(), key=lambda pair: (pair[0][0] or "", ROOM_ORDER.index(pair[0][1]) if pair[0][1] in ROOM_ORDER else 99)):
            items.sort(key=lambda item: item.start_minutes)
            confidence_counts = Counter(item.confidence for item in items)
            summaries.append(
                ProbableTimetableRoomSummary(
                    year=year,
                    event_day=day,
                    room_name=items[0].room_name,
                    room_slug=room_slug,
                    room_capacity=items[0].room_capacity,
                    slot_count=len(items),
                    first_start_time=items[0].start_time,
                    last_end_time=items[-1].end_time,
                    average_demand_score=round(sum(item.demand_score for item in items) / len(items), 2),
                    max_expected_pressure_score=round(max(item.expected_pressure_score for item in items), 2),
                    headliner_slots=sum(1 for item in items if item.is_headliner_slot),
                    confidence_breakdown={key: confidence_counts[key] for key in sorted(confidence_counts)},
                )
            )
        return summaries

    def integrity_report(self, year: int = 2026, *, max_overlaps: int = 25) -> ProbableTimetableIntegrityReport:
        """Return integrity checks for probable timetable rows."""
        self._ensure_probable_timetable(year)
        rows = self._all_slots(year)
        incomplete_slots = sum(1 for row in rows if not row.artist_slug or not row.room_slug or not row.start_time or not row.end_time)
        invalid_duration_slots = sum(1 for row in rows if row.duration_minutes <= 0 or row.end_minutes <= row.start_minutes)
        duplicates = len(rows) - len({row.artist_slug for row in rows})
        invalid_rooms = sum(1 for row in rows if row.room_slug not in ROOM_ORDER)
        capacity_pressure_violations = sum(1 for row in rows if row.expected_pressure_score > 100.0)

        overlaps: list[ProbableTimetableOverlapIssue] = []
        grouped: dict[tuple[str, str], list[V2ProbableTimetableSlotModel]] = defaultdict(list)
        for row in rows:
            grouped[(row.event_day, row.room_slug)].append(row)
        for (event_day, room_slug), items in grouped.items():
            items.sort(key=lambda item: item.start_minutes)
            for previous, current in zip(items, items[1:]):
                if current.start_minutes < previous.end_minutes:
                    overlaps.append(
                        ProbableTimetableOverlapIssue(
                            year=year,
                            event_day=event_day,
                            room_slug=room_slug,
                            first_artist=previous.artist_name,
                            first_start_time=previous.start_time,
                            first_end_time=previous.end_time,
                            second_artist=current.artist_name,
                            second_start_time=current.start_time,
                            second_end_time=current.end_time,
                        )
                    )
                    if len(overlaps) >= max_overlaps:
                        break

        rooms_used = sorted({row.room_name for row in rows})
        valid = not any([incomplete_slots, invalid_duration_slots, duplicates, invalid_rooms, capacity_pressure_violations, overlaps])
        return ProbableTimetableIntegrityReport(
            valid=valid,
            official_available=False,
            source_status=SOURCE_STATUS,
            incomplete_slots=incomplete_slots,
            invalid_duration_slots=invalid_duration_slots,
            overlap_count=len(overlaps),
            duplicate_artist_count=duplicates,
            invalid_room_count=invalid_rooms,
            capacity_pressure_violations=capacity_pressure_violations,
            overlaps=overlaps,
            rooms_used=rooms_used,
            is_seven_room_fabrik_model=set(rooms_used).issubset(set(ROOM_NAMES.values())) and len({row.room_slug for row in rows}) <= 7,
            notes=[
                "The probable timetable uses the verified seven-room Fabrik model.",
                "The result is a prediction and must not be treated as an official schedule.",
            ],
        )

    def _ensure_inputs(self, year: int) -> None:
        """Ensure historical and demand inputs exist before V2.8 generation."""
        historical_count = self.db.scalar(select(func.count()).select_from(HistoricalTimetableSlotModel)) or 0
        if historical_count == 0:
            HistoricalTimetableService(self.db).import_seed(reset=True)

        demand_count = self.db.scalar(
            select(func.count()).select_from(V2ArtistDemandPredictionModel).where(V2ArtistDemandPredictionModel.year == year)
        ) or 0
        if demand_count == 0:
            DemandModelService(self.db).rebuild(year, reset=True)

    def _ensure_probable_timetable(self, year: int) -> None:
        """Rebuild lazily when no V2.8 probable slots exist."""
        count = self.db.scalar(
            select(func.count()).select_from(V2ProbableTimetableSlotModel).where(V2ProbableTimetableSlotModel.year == year)
        ) or 0
        if count == 0:
            self.rebuild(year, reset=True)

    def _demand_predictions(self, year: int) -> list[V2ArtistDemandPredictionModel]:
        """Return persisted V2.7 rows ordered by demand rank."""
        rows = list(
            self.db.scalars(
                select(V2ArtistDemandPredictionModel)
                .where(V2ArtistDemandPredictionModel.year == year)
                .order_by(V2ArtistDemandPredictionModel.rank.asc().nullslast(), V2ArtistDemandPredictionModel.demand_score.desc())
            ).all()
        )
        return rows

    def _room_inventory(self) -> dict[str, dict[str, Any]]:
        """Return canonical seven-room inventory with capacity fallbacks."""
        rows = list(self.db.scalars(select(RoomModel)).all())
        by_slug: dict[str, RoomModel] = {self._normalize_room_filter(row.name): row for row in rows}
        inventory = {}
        for slug in ROOM_ORDER:
            row = by_slug.get(slug)
            inventory[slug] = {
                "slug": slug,
                "name": ROOM_NAMES[slug],
                "capacity": int(row.estimated_capacity or row.max_capacity or row.min_capacity or DEFAULT_ROOM_CAPACITY[slug]) if row else DEFAULT_ROOM_CAPACITY[slug],
            }
        return inventory

    def _historical_patterns(self) -> dict[str, Any]:
        """Learn compact room/genre/slot patterns from V2.6 historical rows."""
        slots = list(self.db.scalars(select(HistoricalTimetableSlotModel)).all())
        genre_by_artist = self._genre_by_artist()
        artist_rooms: dict[str, Counter[str]] = defaultdict(Counter)
        genre_rooms: dict[str, Counter[str]] = defaultdict(Counter)
        genre_slot_types: dict[str, Counter[str]] = defaultdict(Counter)
        room_headliner_times: dict[str, Counter[int]] = defaultdict(Counter)

        for slot in slots:
            if slot.artist_slug:
                artist_rooms[slot.artist_slug][slot.room_slug] += 1
                genre = genre_by_artist.get(slot.artist_slug, "Unknown")
                genre_rooms[genre][slot.room_slug] += 1
                genre_slot_types[genre][slot.slot_type] += 1
            if slot.is_headliner_slot:
                room_headliner_times[slot.room_slug][slot.start_minutes] += 1

        return {
            "artist_rooms": artist_rooms,
            "genre_rooms": genre_rooms,
            "genre_slot_types": genre_slot_types,
            "room_headliner_times": room_headliner_times,
        }

    def _assign_rooms_and_days(
        self,
        predictions: list[V2ArtistDemandPredictionModel],
        historical_patterns: dict[str, Any],
    ) -> tuple[list[CandidateAssignment], list[str]]:
        """Assign each artist to the most probable day/room bucket."""
        buckets: dict[tuple[str, str], list[CandidateAssignment]] = defaultdict(list)
        day_demand = {"friday": 0.0, "saturday": 0.0}
        assignments: list[CandidateAssignment] = []
        warnings: list[str] = []

        for prediction in predictions:
            candidates: list[tuple[float, str, str, list[ProbableTimetableReason], dict[str, Any]]] = []
            for day, rooms in ROOM_DAY_PLAN.items():
                for room_slug, plan in rooms.items():
                    if len(buckets[(day, room_slug)]) >= plan["slots"]:
                        continue
                    room_score, reasons, pattern = self._room_fit_score(prediction, room_slug, historical_patterns)
                    balance_score = self._day_balance_score(day, day_demand, prediction.demand_score)
                    utilization_penalty = len(buckets[(day, room_slug)]) * 1.15
                    total = normalize_score(room_score * 0.78 + balance_score * 0.22 - utilization_penalty)
                    reasons.append(
                        ProbableTimetableReason(
                            key="day_balance",
                            label="Day balance",
                            weight=round(balance_score, 2),
                            explanation="Top-demand acts are distributed across Friday and Saturday instead of stacked on one day.",
                        )
                    )
                    candidates.append((total, day, room_slug, reasons, pattern))

            if not candidates:
                warnings.append(f"No available room/day slot for {prediction.artist_slug}; artist left unassigned.")
                continue

            candidates.sort(key=lambda item: item[0], reverse=True)
            score, day, room_slug, reasons, pattern = candidates[0]
            assignment = CandidateAssignment(
                prediction=prediction,
                day=day,
                room_slug=room_slug,
                room_score=score,
                historical_pattern=pattern,
                reasons=reasons,
            )
            buckets[(day, room_slug)].append(assignment)
            assignments.append(assignment)
            day_demand[day] += prediction.demand_score

        return assignments, warnings

    def _materialize_slots(
        self,
        assignments: list[CandidateAssignment],
        *,
        room_inventory: dict[str, dict[str, Any]],
        generated_at: datetime,
        year: int,
    ) -> list[V2ProbableTimetableSlotModel]:
        """Turn room/day assignments into ordered one-hour slots."""
        artists_by_slug = {row.slug: row for row in self.db.scalars(select(ArtistModel)).all()}
        grouped: dict[tuple[str, str], list[CandidateAssignment]] = defaultdict(list)
        for assignment in assignments:
            grouped[(assignment.day, assignment.room_slug)].append(assignment)

        slots: list[V2ProbableTimetableSlotModel] = []
        for (day, room_slug), items in grouped.items():
            ordered_positions = self._ranked_slot_positions(len(items))
            sorted_items = sorted(items, key=lambda item: (-item.prediction.demand_score, item.prediction.artist_name.lower()))
            positioned = list(zip(ordered_positions, sorted_items))
            for position, assignment in sorted(positioned, key=lambda item: item[0]):
                prediction = assignment.prediction
                room = room_inventory[room_slug]
                plan = ROOM_DAY_PLAN[day][room_slug]
                start_minutes = int(plan["start"] * 60 + position * 60)
                end_minutes = start_minutes + 60
                slot_type = self._slot_type(position, len(items), prediction)
                is_warmup = slot_type == "warm_up"
                is_closing = slot_type == "closing"
                is_headliner = slot_type in {"headliner", "closing"}
                confidence, probability = self._confidence_and_probability(assignment, slot_type=slot_type, prediction=prediction)
                pressure = self._expected_pressure(prediction.demand_score, room["capacity"], slot_type)
                artist = artists_by_slug.get(prediction.artist_slug)
                show_name, performance_type = self._show_context(artist, year)
                reasons = [*assignment.reasons, self._slot_reason(slot_type, position, len(items))]
                warnings = [] if confidence != "low" else ["Low confidence: external or historical signals are limited for this artist."]

                slots.append(
                    V2ProbableTimetableSlotModel(
                        year=year,
                        timetable_kind="probable",
                        event_day=day,
                        festival_day=1 if day == "friday" else 2,
                        date_label=f"Nexus Festival {year} {day.title()} (probable, not official)",
                        room_name=room["name"],
                        room_slug=room_slug,
                        room_capacity=room["capacity"],
                        artist_id=artist.id if artist else prediction.artist_id,
                        artist_slug=prediction.artist_slug,
                        artist_name=prediction.artist_name,
                        artist_rank=prediction.rank,
                        show_name=show_name or prediction.artist_name,
                        performance_type=performance_type,
                        main_genre=prediction.main_genre,
                        secondary_genres_json=prediction.secondary_genres_json,
                        start_time=self._minutes_to_time(start_minutes),
                        end_time=self._minutes_to_time(end_minutes),
                        start_minutes=start_minutes,
                        end_minutes=end_minutes,
                        duration_minutes=60,
                        slot_order=position + 1,
                        slot_type=slot_type,
                        is_headliner_slot=is_headliner,
                        is_closing_slot=is_closing,
                        is_warmup_slot=is_warmup,
                        is_special_show=performance_type in {"special_show", "b2b", "versus", "collaboration"},
                        popularity_score=round(prediction.popularity_score, 2),
                        career_score=round(prediction.career_score, 2),
                        momentum_score=round(prediction.momentum_score, 2),
                        nexus_affinity_score=round(prediction.nexus_affinity_score, 2),
                        demand_score=round(prediction.demand_score, 2),
                        expected_pressure_score=pressure,
                        probability_score=probability,
                        crowd_risk=prediction.crowd_risk,
                        confidence=confidence,
                        model_version=MODEL_VERSION,
                        method=MODEL_METHOD,
                        official_status=OFFICIAL_STATUS,
                        source_status=SOURCE_STATUS,
                        is_official=False,
                        reason_json=dumps_json([reason.model_dump(mode="json") for reason in reasons]),
                        warning_json=dumps_json(warnings),
                        historical_pattern_json=dumps_json(assignment.historical_pattern),
                        raw_json=dumps_json(
                            {
                                "assignment_room_score": round(assignment.room_score, 2),
                                "v2_demand_model_version": prediction.model_version,
                                "is_official": False,
                            }
                        ),
                        generated_at=generated_at,
                    )
                )
        return slots

    def _room_fit_score(
        self,
        prediction: V2ArtistDemandPredictionModel,
        room_slug: str,
        historical_patterns: dict[str, Any],
    ) -> tuple[float, list[ProbableTimetableReason], dict[str, Any]]:
        """Score how likely an artist is to be placed in a room."""
        genre = prediction.main_genre or "Unknown"
        genre_prior = GENRE_ROOM_PRIORS.get(genre, GENRE_ROOM_PRIORS["Unknown"]).get(room_slug, 42.0)
        demand_capacity = self._demand_capacity_fit(prediction.demand_score, room_slug)
        artist_room_count = historical_patterns["artist_rooms"].get(prediction.artist_slug, Counter())
        artist_total = sum(artist_room_count.values())
        artist_room_share = artist_room_count[room_slug] / artist_total * 100.0 if artist_total else 0.0
        genre_room_count = historical_patterns["genre_rooms"].get(genre, Counter())
        genre_total = sum(genre_room_count.values())
        genre_room_share = genre_room_count[room_slug] / genre_total * 100.0 if genre_total else 0.0
        score = normalize_score(genre_prior * 0.38 + demand_capacity * 0.30 + artist_room_share * 0.18 + genre_room_share * 0.14)
        reasons = [
            ProbableTimetableReason(
                key="genre_room_fit",
                label="Genre-room fit",
                weight=round(genre_prior, 2),
                explanation=f"{genre} historically and stylistically fits {ROOM_NAMES[room_slug]} with this prior.",
            ),
            ProbableTimetableReason(
                key="demand_capacity_fit",
                label="Demand/capacity fit",
                weight=round(demand_capacity, 2),
                explanation="The artist demand score is matched against the relative capacity and prestige of the room.",
            ),
        ]
        if artist_room_share > 0:
            reasons.append(
                ProbableTimetableReason(
                    key="artist_historical_room_pattern",
                    label="Artist historical room pattern",
                    weight=round(artist_room_share, 2),
                    explanation=f"Historical timetable data has previously placed this artist in {ROOM_NAMES[room_slug]} or an equivalent room.",
                )
            )
        if genre_room_share > 0:
            reasons.append(
                ProbableTimetableReason(
                    key="genre_historical_room_pattern",
                    label="Genre historical room pattern",
                    weight=round(genre_room_share, 2),
                    explanation=f"Historical timetable data often maps {genre} acts to this room family.",
                )
            )
        pattern = {
            "artist_room_counts": dict(artist_room_count),
            "artist_room_share": round(artist_room_share, 2),
            "genre_room_counts": dict(genre_room_count),
            "genre_room_share": round(genre_room_share, 2),
        }
        return score, reasons, pattern

    @staticmethod
    def _demand_capacity_fit(demand_score: float, room_slug: str) -> float:
        """Prefer larger rooms for top demand and smaller rooms for lower demand."""
        room_capacity_rank = {
            "main-room": 100.0,
            "open-air": 82.0,
            "hangar": 72.0,
            "area-19": 56.0,
            "satelite": 52.0,
            "club-area": 38.0,
            "crystal-area": 34.0,
        }[room_slug]
        if demand_score >= 75:
            return room_capacity_rank
        if demand_score >= 55:
            return 100.0 - abs(room_capacity_rank - 72.0)
        if demand_score >= 35:
            return 100.0 - abs(room_capacity_rank - 55.0)
        return 100.0 - abs(room_capacity_rank - 38.0)

    @staticmethod
    def _day_balance_score(day: str, day_demand: dict[str, float], demand_score: float) -> float:
        """Score a candidate day based on demand balance between days."""
        other_day = "saturday" if day == "friday" else "friday"
        projected_gap = abs((day_demand[day] + demand_score) - day_demand[other_day])
        return normalize_score(100.0 - min(60.0, projected_gap / 8.0))

    @staticmethod
    def _ranked_slot_positions(count: int) -> list[int]:
        """Return preferred positions for assigning highest-demand acts first."""
        if count <= 0:
            return []
        center = max(0, count // 2)
        preferred = [center, min(count - 1, center + 1), max(0, center - 1), count - 1, max(0, center - 2), min(count - 1, center + 2)]
        preferred.extend(range(count))
        result = []
        for position in preferred:
            if 0 <= position < count and position not in result:
                result.append(position)
        return result[:count]

    @staticmethod
    def _slot_type(position: int, count: int, prediction: V2ArtistDemandPredictionModel) -> str:
        """Classify a one-hour slot using room order and demand."""
        if position == 0:
            return "warm_up"
        if position == count - 1:
            return "closing"
        peak_positions = {max(1, count // 2), min(count - 2, count // 2 + 1)}
        if position in peak_positions or (prediction.rank is not None and prediction.rank <= 18) or prediction.demand_score >= 68:
            return "headliner"
        return "standard"

    @staticmethod
    def _slot_reason(slot_type: str, position: int, count: int) -> ProbableTimetableReason:
        """Explain why a time slot is plausible."""
        label = {
            "warm_up": "Warm-up pattern",
            "standard": "Standard build-up pattern",
            "headliner": "Peak/headliner pattern",
            "closing": "Closing pattern",
        }[slot_type]
        return ProbableTimetableReason(
            key="slot_pattern",
            label=label,
            weight=85.0 if slot_type in {"headliner", "closing"} else 68.0,
            explanation=f"Slot order {position + 1}/{count} follows observed Nexus room flow: warm-up, build-up, peak and closing.",
        )

    def _confidence_and_probability(
        self,
        assignment: CandidateAssignment,
        *,
        slot_type: str,
        prediction: V2ArtistDemandPredictionModel,
    ) -> tuple[str, float]:
        """Compute confidence label and probability score for a slot."""
        demand_confidence = CONFIDENCE_SCORES.get(prediction.confidence, 60.0)
        slot_weight = {"warm_up": 58.0, "standard": 68.0, "headliner": 82.0, "closing": 74.0}[slot_type]
        pattern_bonus = min(14.0, float(assignment.historical_pattern.get("artist_room_share", 0.0)) * 0.18)
        probability = normalize_score(assignment.room_score * 0.50 + demand_confidence * 0.26 + slot_weight * 0.20 + pattern_bonus)
        if probability >= 82 and prediction.confidence in {"high", "medium_high"}:
            return "high", probability
        if probability >= 72:
            return "medium_high", probability
        if probability >= 55:
            return "medium", probability
        return "low", probability

    @staticmethod
    def _expected_pressure(demand_score: float, capacity: int, slot_type: str) -> float:
        """Estimate relative pressure without claiming real attendance counts."""
        capacity_factor = max(0.65, min(1.65, 1800 / max(capacity, 1)))
        time_multiplier = TIME_MULTIPLIERS_BY_POSITION[slot_type]
        pressure = demand_score * 0.78 * time_multiplier * capacity_factor + (12.0 if slot_type == "headliner" else 0.0)
        return normalize_score(pressure)

    def _show_context(self, artist: ArtistModel | None, year: int) -> tuple[str | None, str]:
        """Extract the 2026 show name/performance type from artist appearances."""
        if not artist:
            return None, "solo"
        appearances = loads_json(artist.appearances_json, [])
        for appearance in appearances:
            if int(appearance.get("year", 0) or 0) == year:
                return appearance.get("performance_display_name") or artist.name, appearance.get("performance_type") or "solo"
        return artist.name, "solo"

    def _genre_by_artist(self) -> dict[str, str]:
        """Return primary genre lookup from V2.5 rows, falling back to artist seed."""
        mapping: dict[str, str] = {}
        rows = list(self.db.scalars(select(ArtistGenreModel).where(ArtistGenreModel.is_primary.is_(True))).all())
        for row in rows:
            mapping[row.artist_slug] = row.genre
        for artist in self.db.scalars(select(ArtistModel)).all():
            mapping.setdefault(artist.slug, artist.primary_genre_seed or "Unknown")
        return mapping

    @staticmethod
    def _minutes_to_time(value: int) -> str:
        """Convert absolute event minutes into HH:MM with after-midnight wrap."""
        wrapped = value % (24 * 60)
        return f"{wrapped // 60:02d}:{wrapped % 60:02d}"

    @staticmethod
    def _normalize_room_filter(value: str) -> str:
        """Normalize canonical room names and aliases into V2 room slugs."""
        normalized = value.strip().lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        normalized = normalized.replace("/", " ").replace("-", " ")
        compact = " ".join(normalized.split())
        aliases = {
            "main": "main-room",
            "main room": "main-room",
            "open air": "open-air",
            "openair": "open-air",
            "hangar": "hangar",
            "area 19": "area-19",
            "area19": "area-19",
            "satelite": "satelite",
            "satellite": "satelite",
            "club": "club-area",
            "club area": "club-area",
            "rave area": "club-area",
            "rave area club": "club-area",
            "club 360": "club-area",
            "crystal": "crystal-area",
            "crystal area": "crystal-area",
            "new crystal": "crystal-area",
            "new crystal area": "crystal-area",
        }
        return aliases.get(compact, compact.replace(" ", "-"))

    def _all_slots(self, year: int) -> list[V2ProbableTimetableSlotModel]:
        """Return all probable slots ordered for display."""
        return list(
            self.db.scalars(
                select(V2ProbableTimetableSlotModel)
                .where(V2ProbableTimetableSlotModel.year == year)
                .order_by(
                    V2ProbableTimetableSlotModel.event_day.asc(),
                    V2ProbableTimetableSlotModel.room_slug.asc(),
                    V2ProbableTimetableSlotModel.start_minutes.asc(),
                )
            ).all()
        )

    def _day_summaries(self, rows: list[V2ProbableTimetableSlotModel]) -> list[ProbableTimetableDaySummary]:
        """Build day-level summaries from slot rows."""
        grouped: dict[str, list[V2ProbableTimetableSlotModel]] = defaultdict(list)
        for row in rows:
            grouped[row.event_day].append(row)
        summaries = []
        for day, items in sorted(grouped.items()):
            items.sort(key=lambda row: row.start_minutes)
            summaries.append(
                ProbableTimetableDaySummary(
                    event_day=day,
                    festival_day=1 if day == "friday" else 2,
                    date_label=f"Nexus Festival 2026 {day.title()} (probable, not official)",
                    slot_count=len(items),
                    room_count=len({item.room_slug for item in items}),
                    first_start_time=items[0].start_time,
                    last_end_time=max(items, key=lambda item: item.end_minutes).end_time,
                    average_demand_score=round(sum(item.demand_score for item in items) / len(items), 2),
                    max_expected_pressure_score=round(max(item.expected_pressure_score for item in items), 2),
                )
            )
        return summaries

    def _row_to_slot(self, row: V2ProbableTimetableSlotModel) -> ProbableTimetableSlotRecord:
        """Convert one ORM row into the public V2.8 schema."""
        generated_at = row.generated_at.replace(tzinfo=timezone.utc).isoformat() if row.generated_at else ""
        return ProbableTimetableSlotRecord(
            id=row.id,
            year=row.year,
            timetable_kind=row.timetable_kind,
            event_day=row.event_day,
            festival_day=row.festival_day,
            date_label=row.date_label,
            room_name=row.room_name,
            room_slug=row.room_slug,
            room_capacity=row.room_capacity,
            artist_slug=row.artist_slug,
            artist_name=row.artist_name,
            artist_rank=row.artist_rank,
            show_name=row.show_name,
            performance_type=row.performance_type,
            main_genre=row.main_genre,
            secondary_genres=list(loads_json(row.secondary_genres_json, [])),
            start_time=row.start_time,
            end_time=row.end_time,
            start_minutes=row.start_minutes,
            end_minutes=row.end_minutes,
            duration_minutes=row.duration_minutes,
            slot_order=row.slot_order,
            slot_type=row.slot_type,
            is_headliner_slot=row.is_headliner_slot,
            is_closing_slot=row.is_closing_slot,
            is_warmup_slot=row.is_warmup_slot,
            is_special_show=row.is_special_show,
            popularity_score=round(row.popularity_score, 2),
            career_score=round(row.career_score, 2),
            momentum_score=round(row.momentum_score, 2),
            nexus_affinity_score=round(row.nexus_affinity_score, 2),
            demand_score=round(row.demand_score, 2),
            expected_pressure_score=round(row.expected_pressure_score, 2),
            probability_score=round(row.probability_score, 2),
            crowd_risk=row.crowd_risk,
            confidence=row.confidence,
            model_version=row.model_version,
            method=row.method,
            official_status=row.official_status,
            source_status=row.source_status,
            is_official=row.is_official,
            reasons=[ProbableTimetableReason(**item) for item in loads_json(row.reason_json, [])],
            warnings=list(loads_json(row.warning_json, [])),
            historical_pattern=dict(loads_json(row.historical_pattern_json, {})),
            generated_at=generated_at,
        )
