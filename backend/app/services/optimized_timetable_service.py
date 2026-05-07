"""V2.9 optimized timetable generator.

This service consumes the already-closed V2.8 probable timetable and produces
three non-official optimized variants:

A. anti_crowding_extreme — minimize crowd pressure and risky small-room peaks.
B. balanced — compromise between flow, room fit and protecting top sets.
C. fan_experience — maximize the chance of seeing top artists with fewer severe clashes.

OR-Tools is used when the package is installed. A deterministic heuristic fallback
keeps local validation stable before users rerun `pip install -r requirements.txt`.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import V2OptimizedTimetableSlotModel, V2ProbableTimetableSlotModel
from app.repositories.sqlite_repository import SQLiteRepository
from app.schemas.optimized_timetable import (
    OptimizedTimetableComparison,
    OptimizedTimetableConstraint,
    OptimizedTimetableCoverage,
    OptimizedTimetableDaySummary,
    OptimizedTimetableIntegrityReport,
    OptimizedTimetableOverlapIssue,
    OptimizedTimetableReason,
    OptimizedTimetableRebuildResult,
    OptimizedTimetableSlotList,
    OptimizedTimetableSlotRecord,
    OptimizedTimetableVariantSummary,
    OptimizedTimetableYearOverview,
)
from app.services.database_seed_service import dumps_json, ensure_database_ready, loads_json
from app.services.probable_timetable_service import ProbableTimetableService
from app.services.scoring_service import normalize_score

try:  # pragma: no cover - availability depends on local install state.
    from ortools.sat.python import cp_model
except Exception:  # pragma: no cover - fallback is tested indirectly.
    cp_model = None

MODEL_VERSION = "v2.9-optimized-timetable-variants"
MODEL_METHOD = "ortools_cp_sat_assignment_with_heuristic_fallback"
OFFICIAL_STATUS = "optimized_not_official"
SOURCE_STATUS = "no_official_timetable_yet"

VARIANT_ORDER = ["anti_crowding_extreme", "balanced", "fan_experience"]
VARIANT_CONFIGS: dict[str, dict[str, Any]] = {
    "anti_crowding_extreme": {
        "name": "A · Anti-aglomeraciones extremo",
        "description": "Spreads high-demand artists across room sizes and hours to reduce severe crowd-pressure peaks.",
        "crowding_weight": 0.62,
        "conflict_weight": 0.25,
        "experience_weight": 0.13,
        "strategy": "spread_top_artists",
    },
    "balanced": {
        "name": "B · Equilibrado",
        "description": "Balances crowd flow with strong room fit and reasonable protection for main sets.",
        "crowding_weight": 0.40,
        "conflict_weight": 0.25,
        "experience_weight": 0.35,
        "strategy": "balanced_room_fit",
    },
    "fan_experience": {
        "name": "C · Experiencia fan",
        "description": "Prioritizes sequential top-artist viewing and protects main sets from severe clashes.",
        "crowding_weight": 0.20,
        "conflict_weight": 0.25,
        "experience_weight": 0.55,
        "strategy": "sequential_top_sets",
    },
}

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

GENRE_ROOM_PRIORS: dict[str, dict[str, float]] = {
    "Classic / Legacy Hardstyle": {"main-room": 98, "open-air": 86, "satelite": 76, "hangar": 60},
    "Euphoric Hardstyle": {"open-air": 94, "main-room": 86, "satelite": 78, "hangar": 58},
    "Mainstage Hard Dance": {"main-room": 92, "open-air": 88, "satelite": 70, "hangar": 64},
    "Rawstyle": {"main-room": 86, "open-air": 84, "hangar": 78, "area-19": 72},
    "Xtra Raw": {"hangar": 90, "area-19": 86, "open-air": 76, "main-room": 70},
    "Hardcore": {"hangar": 94, "main-room": 80, "area-19": 72, "club-area": 66},
    "Uptempo Hardcore": {"area-19": 92, "hangar": 86, "club-area": 78, "crystal-area": 66},
    "Frenchcore": {"hangar": 90, "satelite": 80, "main-room": 72, "open-air": 66},
    "Industrial Hardcore": {"hangar": 88, "club-area": 80, "area-19": 74, "crystal-area": 70},
    "Happy Hardcore": {"satelite": 90, "open-air": 78, "main-room": 72, "crystal-area": 62},
    "Freestyle / Hard Dance": {"satelite": 84, "open-air": 74, "club-area": 68, "main-room": 62},
    "Unknown": {"crystal-area": 74, "club-area": 70, "satelite": 66, "area-19": 62},
}

PRIME_TIME_BONUS = {
    "warm_up": 35.0,
    "standard": 62.0,
    "headliner": 92.0,
    "closing": 86.0,
    "special_show": 78.0,
}


@dataclass(frozen=True)
class CandidateSlot:
    """A reusable empty position derived from V2.8 probable slots."""

    source: V2ProbableTimetableSlotModel
    event_day: str
    festival_day: int
    date_label: str | None
    room_name: str
    room_slug: str
    room_capacity: int | None
    start_time: str
    end_time: str
    start_minutes: int
    end_minutes: int
    duration_minutes: int
    slot_order: int
    slot_type: str
    is_headliner_slot: bool
    is_closing_slot: bool
    is_warmup_slot: bool
    is_special_show: bool


@dataclass(frozen=True)
class ArtistPayload:
    """Artist fields copied from a V2.8 probable slot."""

    source: V2ProbableTimetableSlotModel
    artist_id: int | None
    artist_slug: str
    artist_name: str
    artist_rank: int | None
    show_name: str
    performance_type: str
    main_genre: str
    secondary_genres_json: str
    popularity_score: float
    career_score: float
    momentum_score: float
    nexus_affinity_score: float
    demand_score: float
    crowd_risk: str
    original_room_slug: str
    original_start_minutes: int
    probable_slot_id: int | None


class OptimizedTimetableService:
    """Generate and expose V2.9 optimized timetable variants."""

    def __init__(self, db: Session) -> None:
        """Use one request-scoped database session."""
        self.db = db
        ensure_database_ready(self.db)
        self.repository = SQLiteRepository(db)

    def rebuild(self, year: int = 2026, *, reset: bool = True) -> OptimizedTimetableRebuildResult:
        """Build all optimized variants for a year."""
        if self.repository.get_edition(year) is None:
            raise ValueError(f"Edition {year} was not found.")

        probable_service = ProbableTimetableService(self.db)
        probable_service.rebuild(year, reset=False)
        probable_rows = self._probable_rows(year)
        if not probable_rows:
            raise ValueError(f"V2.8 probable timetable could not be generated for {year}.")

        generated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if reset:
            self.db.execute(delete(V2OptimizedTimetableSlotModel).where(V2OptimizedTimetableSlotModel.year == year))
            self.db.commit()

        slots: list[V2OptimizedTimetableSlotModel] = []
        warnings: list[str] = []
        for variant_key in VARIANT_ORDER:
            variant_slots, variant_warnings = self._build_variant(year, variant_key, probable_rows, generated_at)
            slots.extend(variant_slots)
            warnings.extend(variant_warnings)

        for slot in slots:
            existing = self.db.scalar(
                select(V2OptimizedTimetableSlotModel).where(
                    V2OptimizedTimetableSlotModel.year == year,
                    V2OptimizedTimetableSlotModel.variant_key == slot.variant_key,
                    V2OptimizedTimetableSlotModel.artist_slug == slot.artist_slug,
                )
            )
            if existing is not None:
                slot.id = existing.id
                slot.created_at = existing.created_at
            self.db.merge(slot)

        self.db.commit()
        assigned = Counter(slot.variant_key for slot in slots)
        return OptimizedTimetableRebuildResult(
            year=year,
            model_version=MODEL_VERSION,
            method=MODEL_METHOD,
            solver_status=self._solver_status(),
            variants=len(VARIANT_ORDER),
            variant_keys=list(VARIANT_ORDER),
            slots=len(slots),
            assigned_artists_per_variant={key: assigned[key] for key in VARIANT_ORDER},
            official_available=False,
            source_status=SOURCE_STATUS,
            generated_at=generated_at.replace(tzinfo=timezone.utc).isoformat(),
            warnings=warnings,
        )

    def coverage(self, year: int = 2026) -> OptimizedTimetableCoverage | None:
        """Return coverage counters for all optimized variants."""
        if self.repository.get_edition(year) is None:
            return None
        self._ensure_optimized(year)
        rows = self._all_slots(year)
        generated_at = max((row.generated_at for row in rows if row.generated_at), default=None)
        slots_per_variant = Counter(row.variant_key for row in rows)
        artists_per_variant: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            artists_per_variant[row.variant_key].add(row.artist_slug)
        variant_keys = [key for key in VARIANT_ORDER if slots_per_variant[key] > 0]
        return OptimizedTimetableCoverage(
            year=year,
            expected_variants=len(VARIANT_ORDER),
            generated_variants=len(variant_keys),
            variant_keys=variant_keys,
            total_slots=len(rows),
            slots_per_variant={key: slots_per_variant[key] for key in VARIANT_ORDER},
            assigned_artists_per_variant={key: len(artists_per_variant[key]) for key in VARIANT_ORDER},
            official_available=False,
            source_status=SOURCE_STATUS,
            uses_ortools=cp_model is not None,
            model_version=MODEL_VERSION,
            method=MODEL_METHOD,
            generated_at=generated_at.replace(tzinfo=timezone.utc).isoformat() if generated_at else None,
        )

    def list_variants(self, year: int = 2026) -> list[OptimizedTimetableVariantSummary] | None:
        """Return one metrics summary per optimized variant."""
        if self.repository.get_edition(year) is None:
            return None
        self._ensure_optimized(year)
        return [self._variant_summary(year, key) for key in VARIANT_ORDER]

    def variant_overview(self, year: int, variant_key: str) -> OptimizedTimetableYearOverview | None:
        """Return a full variant overview with slots and day summaries."""
        if self.repository.get_edition(year) is None or variant_key not in VARIANT_CONFIGS:
            return None
        self._ensure_optimized(year)
        rows = self._variant_rows(year, variant_key)
        if not rows:
            return None
        return OptimizedTimetableYearOverview(
            year=year,
            variant=self._variant_summary(year, variant_key),
            days=self._day_summaries(rows),
            slots=[self._row_to_slot(row) for row in rows],
            notes=[
                "This is an optimized non-official scenario, not an official Nexus/Fabrik timetable.",
                "Use the comparison endpoint to choose a strategy depending on crowding, conflicts or fan experience.",
            ],
        )

    def list_slots(
        self,
        year: int,
        *,
        variant_key: str | None = None,
        event_day: str | None = None,
        room: str | None = None,
        artist_slug: str | None = None,
        only_headliners: bool = False,
        limit: int = 200,
        offset: int = 0,
    ) -> OptimizedTimetableSlotList | None:
        """Return optimized slots with filters."""
        if self.repository.get_edition(year) is None:
            return None
        self._ensure_optimized(year)
        query = select(V2OptimizedTimetableSlotModel).where(V2OptimizedTimetableSlotModel.year == year)
        if variant_key:
            query = query.where(V2OptimizedTimetableSlotModel.variant_key == variant_key)
        if event_day:
            query = query.where(V2OptimizedTimetableSlotModel.event_day == event_day.lower())
        if room:
            room_slug = self._normalize_room_slug(room)
            query = query.where(V2OptimizedTimetableSlotModel.room_slug == room_slug)
        if artist_slug:
            query = query.where(V2OptimizedTimetableSlotModel.artist_slug == artist_slug)
        if only_headliners:
            query = query.where(V2OptimizedTimetableSlotModel.is_headliner_slot.is_(True))

        rows = list(
            self.db.scalars(
                query.order_by(
                    V2OptimizedTimetableSlotModel.variant_key.asc(),
                    V2OptimizedTimetableSlotModel.event_day.asc(),
                    V2OptimizedTimetableSlotModel.room_slug.asc(),
                    V2OptimizedTimetableSlotModel.start_minutes.asc(),
                )
            ).all()
        )
        page = rows[offset : offset + limit]
        return OptimizedTimetableSlotList(
            year=year,
            variant_key=variant_key,
            total=len(rows),
            limit=limit,
            offset=offset,
            items=[self._row_to_slot(row) for row in page],
        )

    def get_artist_slot(self, year: int, variant_key: str, artist_slug: str) -> OptimizedTimetableSlotRecord | None:
        """Return one optimized slot for an artist/variant."""
        if self.repository.get_edition(year) is None or variant_key not in VARIANT_CONFIGS:
            return None
        self._ensure_optimized(year)
        row = self.db.scalar(
            select(V2OptimizedTimetableSlotModel).where(
                V2OptimizedTimetableSlotModel.year == year,
                V2OptimizedTimetableSlotModel.variant_key == variant_key,
                V2OptimizedTimetableSlotModel.artist_slug == artist_slug,
            )
        )
        return self._row_to_slot(row) if row else None

    def compare(self, year: int = 2026) -> OptimizedTimetableComparison | None:
        """Compare the three variants with comparable metrics."""
        variants = self.list_variants(year)
        if variants is None:
            return None
        anti = min(variants, key=lambda item: item.average_crowding_score).variant_key
        balanced = max(variants, key=lambda item: item.average_optimization_score).variant_key
        fan = max(variants, key=lambda item: item.average_experience_score).variant_key
        return OptimizedTimetableComparison(
            year=year,
            variants=variants,
            recommended_by_goal={
                "anti_crowding": anti,
                "balanced": balanced,
                "fan_experience": fan,
            },
            metric_notes=[
                "Lower crowding_score is better because it represents pressure risk.",
                "Lower conflict_score is better because it represents severe top-set clashes.",
                "Higher experience_score and optimization_score are better.",
            ],
        )

    def integrity_report(self, year: int = 2026) -> OptimizedTimetableIntegrityReport:
        """Check overlaps, duplicate artists and room-model validity for all variants."""
        self._ensure_optimized(year)
        rows = self._all_slots(year)
        overlaps: list[OptimizedTimetableOverlapIssue] = []
        duplicate_artist_count = 0
        incomplete_slots = 0
        invalid_duration_slots = 0
        invalid_room_count = 0
        allowed_rooms = set(ROOM_ORDER)
        variant_artists: dict[str, set[str]] = defaultdict(set)
        duplicate_pairs: set[tuple[str, str]] = set()

        grouped: dict[tuple[str, str, str], list[V2OptimizedTimetableSlotModel]] = defaultdict(list)
        for row in rows:
            if not row.artist_slug or not row.room_slug or not row.start_time or not row.end_time:
                incomplete_slots += 1
            if row.duration_minutes <= 0 or row.end_minutes <= row.start_minutes:
                invalid_duration_slots += 1
            if row.room_slug not in allowed_rooms:
                invalid_room_count += 1
            artist_key = (row.variant_key, row.artist_slug)
            if row.artist_slug in variant_artists[row.variant_key] and artist_key not in duplicate_pairs:
                duplicate_pairs.add(artist_key)
                duplicate_artist_count += 1
            variant_artists[row.variant_key].add(row.artist_slug)
            grouped[(row.variant_key, row.event_day, row.room_slug)].append(row)

        for (variant_key, day, room_slug), items in grouped.items():
            ordered = sorted(items, key=lambda row: row.start_minutes)
            for previous, current in zip(ordered, ordered[1:]):
                if previous.end_minutes > current.start_minutes:
                    overlaps.append(
                        OptimizedTimetableOverlapIssue(
                            year=year,
                            variant_key=variant_key,
                            event_day=day,
                            room_slug=room_slug,
                            first_artist=previous.artist_slug,
                            first_start_time=previous.start_time,
                            first_end_time=previous.end_time,
                            second_artist=current.artist_slug,
                            second_start_time=current.start_time,
                            second_end_time=current.end_time,
                        )
                    )

        generated_variants = {row.variant_key for row in rows}
        missing_variants = [key for key in VARIANT_ORDER if key not in generated_variants]
        rooms_used = sorted({row.room_name for row in rows})
        valid = (
            not missing_variants
            and incomplete_slots == 0
            and invalid_duration_slots == 0
            and not overlaps
            and duplicate_artist_count == 0
            and invalid_room_count == 0
            and {self._normalize_room_slug(room) for room in rooms_used}.issubset(allowed_rooms)
        )
        return OptimizedTimetableIntegrityReport(
            valid=valid,
            official_available=False,
            source_status=SOURCE_STATUS,
            expected_variants=len(VARIANT_ORDER),
            generated_variants=len(generated_variants),
            missing_variants=missing_variants,
            incomplete_slots=incomplete_slots,
            invalid_duration_slots=invalid_duration_slots,
            overlap_count=len(overlaps),
            duplicate_artist_count=duplicate_artist_count,
            invalid_room_count=invalid_room_count,
            overlaps=overlaps,
            rooms_used=rooms_used,
            is_seven_room_fabrik_model={self._normalize_room_slug(room) for room in rooms_used}.issubset(allowed_rooms),
            notes=[
                "All optimized variants are non-official scenarios.",
                "The optimizer stays inside the verified seven-room Fabrik model.",
            ],
        )

    def _build_variant(
        self,
        year: int,
        variant_key: str,
        probable_rows: list[V2ProbableTimetableSlotModel],
        generated_at: datetime,
    ) -> tuple[list[V2OptimizedTimetableSlotModel], list[str]]:
        """Build one optimized variant from probable rows."""
        config = VARIANT_CONFIGS[variant_key]
        artists = [self._artist_from_probable(row) for row in probable_rows]
        slots = [self._slot_from_probable(row) for row in probable_rows]
        assignments, solver_status, warnings = self._solve_assignment(variant_key, artists, slots)
        rows = []
        for artist, slot in assignments:
            rows.append(self._materialize_row(year, variant_key, config, artist, slot, solver_status, generated_at))
        self._recompute_dynamic_metrics(rows, config)
        return rows, warnings

    def _solve_assignment(
        self,
        variant_key: str,
        artists: list[ArtistPayload],
        slots: list[CandidateSlot],
    ) -> tuple[list[tuple[ArtistPayload, CandidateSlot]], str, list[str]]:
        """Solve artist-slot assignment with OR-Tools when available, then fallback if needed."""
        if cp_model is None:
            return self._heuristic_assignment(variant_key, artists, slots), "heuristic_fallback_no_ortools", [
                "OR-Tools is not installed; deterministic heuristic fallback was used. Run pip install -r requirements.txt to enable CP-SAT."
            ]

        model = cp_model.CpModel()
        max_artists = min(len(artists), len(slots))
        artists = artists[:max_artists]
        variables: dict[tuple[int, int], Any] = {}
        for a_idx in range(max_artists):
            for s_idx in range(len(slots)):
                variables[(a_idx, s_idx)] = model.NewBoolVar(f"a{a_idx}_s{s_idx}")
        for a_idx in range(max_artists):
            model.Add(sum(variables[(a_idx, s_idx)] for s_idx in range(len(slots))) == 1)
        for s_idx in range(len(slots)):
            model.Add(sum(variables[(a_idx, s_idx)] for a_idx in range(max_artists)) <= 1)

        objective_terms = []
        for a_idx, artist in enumerate(artists):
            for s_idx, slot in enumerate(slots):
                score = int(round(self._candidate_score(variant_key, artist, slot) * 100))
                objective_terms.append(score * variables[(a_idx, s_idx)])
        model.Maximize(sum(objective_terms))

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 8.0
        solver.parameters.num_search_workers = 8
        status = solver.Solve(model)
        if status not in {cp_model.OPTIMAL, cp_model.FEASIBLE}:
            return self._heuristic_assignment(variant_key, artists, slots), "heuristic_fallback_after_ortools", [
                f"OR-Tools returned status {solver.StatusName(status)}; deterministic heuristic fallback was used."
            ]

        pairs = []
        used_slots: set[int] = set()
        for a_idx, artist in enumerate(artists):
            for s_idx, slot in enumerate(slots):
                if solver.Value(variables[(a_idx, s_idx)]) == 1:
                    pairs.append((artist, slot))
                    used_slots.add(s_idx)
                    break
        return pairs, f"ortools_{solver.StatusName(status).lower()}", []

    def _heuristic_assignment(self, variant_key: str, artists: list[ArtistPayload], slots: list[CandidateSlot]) -> list[tuple[ArtistPayload, CandidateSlot]]:
        """Deterministic fallback that still honors variant intent."""
        ordered_artists = sorted(artists, key=lambda item: (item.artist_rank or 9999, -item.demand_score, item.artist_slug))
        available = list(slots)
        result: list[tuple[ArtistPayload, CandidateSlot]] = []
        for artist in ordered_artists:
            if not available:
                break
            best_index = max(range(len(available)), key=lambda idx: self._candidate_score(variant_key, artist, available[idx]))
            result.append((artist, available.pop(best_index)))
        return result

    def _candidate_score(self, variant_key: str, artist: ArtistPayload, slot: CandidateSlot) -> float:
        """Return variant-specific score for assigning an artist to an empty slot."""
        config = VARIANT_CONFIGS[variant_key]
        crowding_component = self._crowding_component(artist, slot)
        conflict_component = self._static_conflict_component(variant_key, artist, slot)
        experience_component = self._experience_component(variant_key, artist, slot)
        room_fit = self._genre_room_fit(artist.main_genre, slot.room_slug)
        probable_stability = 6.0 if artist.original_room_slug == slot.room_slug else 0.0
        score = (
            crowding_component * config["crowding_weight"]
            + conflict_component * config["conflict_weight"]
            + experience_component * config["experience_weight"]
            + room_fit * 0.08
            + probable_stability
        )
        if variant_key == "fan_experience" and (artist.artist_rank or 9999) <= 14:
            # Fan experience deliberately creates a more sequential top-card path.
            score += self._top_artist_sequential_bonus(artist, slot)
        if variant_key == "anti_crowding_extreme" and (artist.artist_rank or 9999) <= 18:
            score += self._top_artist_spread_bonus(artist, slot)
        return score

    def _crowding_component(self, artist: ArtistPayload, slot: CandidateSlot) -> float:
        """Higher is better: big-room fit and lower pressure risk."""
        pressure = self._expected_pressure(artist.demand_score, slot.room_capacity)
        capacity_bonus = normalize_score((slot.room_capacity or 0) / 40)
        return normalize_score(100 - max(0.0, pressure - 72) * 1.35 + capacity_bonus * 0.16)

    def _static_conflict_component(self, variant_key: str, artist: ArtistPayload, slot: CandidateSlot) -> float:
        """Approximate conflict avoidance before dynamic recomputation."""
        rank = artist.artist_rank or 9999
        hour = slot.start_minutes // 60
        if variant_key == "fan_experience" and rank <= 14:
            # Prefer one top set per sequential hour around the main path.
            preferred_hour = 22 + ((rank - 1) % 8)
            if preferred_hour >= 24:
                preferred_hour -= 24
            slot_hour = hour % 24
            return normalize_score(96 - abs(slot_hour - preferred_hour) * 14)
        if variant_key == "anti_crowding_extreme" and rank <= 18:
            return 90 if slot.room_slug in {"main-room", "open-air", "hangar", "area-19"} else 72
        return 78 if slot.slot_type in {"headliner", "closing"} else 68

    def _experience_component(self, variant_key: str, artist: ArtistPayload, slot: CandidateSlot) -> float:
        """Higher is better: important artists receive important slots."""
        rank = artist.artist_rank or 9999
        slot_value = PRIME_TIME_BONUS.get(slot.slot_type, 62.0)
        if slot.is_headliner_slot:
            slot_value += 8
        if slot.is_closing_slot:
            slot_value += 4
        if rank <= 10:
            return normalize_score(slot_value + 16)
        if rank <= 25:
            return normalize_score(slot_value + 6)
        if slot.is_warmup_slot:
            return 76
        return normalize_score(slot_value)

    def _top_artist_sequential_bonus(self, artist: ArtistPayload, slot: CandidateSlot) -> float:
        """Encourage a coherent fan path for the highest-ranked artists."""
        rank = artist.artist_rank or 9999
        top_rooms = ["main-room", "open-air", "hangar"]
        room_bonus = 16 if slot.room_slug in top_rooms else 0
        day_bonus = 6 if (rank % 2 == 0 and slot.event_day == "saturday") or (rank % 2 == 1 and slot.event_day == "friday") else 0
        return room_bonus + day_bonus

    def _top_artist_spread_bonus(self, artist: ArtistPayload, slot: CandidateSlot) -> float:
        """Spread top-card artists across medium/large rooms for anti-crowding."""
        rank = artist.artist_rank or 9999
        target_rooms = ["main-room", "open-air", "hangar", "area-19"]
        room_index = (rank - 1) % len(target_rooms)
        return 18 if slot.room_slug == target_rooms[room_index] else 4 if slot.room_slug in target_rooms else 0

    def _materialize_row(
        self,
        year: int,
        variant_key: str,
        config: dict[str, Any],
        artist: ArtistPayload,
        slot: CandidateSlot,
        solver_status: str,
        generated_at: datetime,
    ) -> V2OptimizedTimetableSlotModel:
        """Create one ORM row before dynamic variant metrics are recomputed."""
        pressure = self._expected_pressure(artist.demand_score, slot.room_capacity)
        reasons = [
            OptimizedTimetableReason(
                key="variant_strategy",
                label=config["name"],
                weight=round(config["experience_weight"] * 100, 2),
                explanation=config["description"],
            ).model_dump(),
            OptimizedTimetableReason(
                key="room_genre_fit",
                label="Room/genre fit",
                weight=round(self._genre_room_fit(artist.main_genre, slot.room_slug), 2),
                explanation=f"{artist.main_genre} is assigned to {slot.room_name} with a fitted room-prior score.",
            ).model_dump(),
            OptimizedTimetableReason(
                key="capacity_pressure",
                label="Capacity pressure",
                # ``pressure`` can intentionally reach 140 before clipping because
                # it represents over-capacity risk. Reason weights are displayed
                # as 0-100 explanation intensities, so keep the raw pressure in
                # the dedicated expected_pressure_score field and clamp only this
                # UI/explanation weight to satisfy the schema contract.
                weight=round(self._reason_weight(pressure), 2),
                explanation="Expected pressure is estimated from V2.7 demand score and room capacity.",
            ).model_dump(),
        ]
        constraints = [
            OptimizedTimetableConstraint(
                key="one_artist_one_slot",
                label="One artist per variant",
                severity="hard",
                satisfied=True,
                explanation="Each artist is assigned at most once inside the optimized variant.",
            ).model_dump(),
            OptimizedTimetableConstraint(
                key="one_room_slot_one_artist",
                label="No same-room slot collision",
                severity="hard",
                satisfied=True,
                explanation="Each room/time position is used by at most one artist.",
            ).model_dump(),
            OptimizedTimetableConstraint(
                key="seven_room_model",
                label="Verified seven-room Fabrik model",
                severity="hard",
                satisfied=slot.room_slug in ROOM_ORDER,
                explanation="The optimizer cannot create extra 2025-style phantom stages.",
            ).model_dump(),
        ]
        return V2OptimizedTimetableSlotModel(
            year=year,
            variant_key=variant_key,
            variant_name=config["name"],
            variant_description=config["description"],
            event_day=slot.event_day,
            festival_day=slot.festival_day,
            date_label=f"Nexus Festival {year} {slot.event_day.title()} ({config['name']}, optimized, not official)",
            room_name=slot.room_name,
            room_slug=slot.room_slug,
            room_capacity=slot.room_capacity,
            artist_id=artist.artist_id,
            artist_slug=artist.artist_slug,
            artist_name=artist.artist_name,
            artist_rank=artist.artist_rank,
            show_name=artist.show_name,
            performance_type=artist.performance_type,
            main_genre=artist.main_genre,
            secondary_genres_json=artist.secondary_genres_json,
            start_time=slot.start_time,
            end_time=slot.end_time,
            start_minutes=slot.start_minutes,
            end_minutes=slot.end_minutes,
            duration_minutes=slot.duration_minutes,
            slot_order=slot.slot_order,
            slot_type=slot.slot_type,
            is_headliner_slot=slot.is_headliner_slot,
            is_closing_slot=slot.is_closing_slot,
            is_warmup_slot=slot.is_warmup_slot,
            is_special_show=slot.is_special_show,
            popularity_score=artist.popularity_score,
            career_score=artist.career_score,
            momentum_score=artist.momentum_score,
            nexus_affinity_score=artist.nexus_affinity_score,
            demand_score=artist.demand_score,
            expected_pressure_score=round(pressure, 2),
            crowding_score=round(min(100.0, pressure), 2),
            conflict_score=0.0,
            experience_score=round(self._experience_component(variant_key, artist, slot), 2),
            optimization_score=0.0,
            crowd_risk=self._crowd_risk_from_pressure(pressure),
            original_room_slug=artist.original_room_slug,
            original_start_minutes=artist.original_start_minutes,
            probable_slot_id=artist.probable_slot_id,
            model_version=MODEL_VERSION,
            method=MODEL_METHOD,
            solver_status=solver_status,
            official_status=OFFICIAL_STATUS,
            source_status=SOURCE_STATUS,
            is_official=False,
            reason_json=dumps_json(reasons),
            constraint_json=dumps_json(constraints),
            warning_json=dumps_json([]),
            raw_json=dumps_json({"variant_key": variant_key, "source": "v2.8_probable_timetable"}),
            generated_at=generated_at,
        )

    def _recompute_dynamic_metrics(self, rows: list[V2OptimizedTimetableSlotModel], config: dict[str, Any]) -> None:
        """Compute conflict and final optimization scores after the assignment is known."""
        by_time: dict[tuple[str, int], list[V2OptimizedTimetableSlotModel]] = defaultdict(list)
        for row in rows:
            by_time[(row.event_day, row.start_minutes)].append(row)

        for row in rows:
            concurrent = by_time[(row.event_day, row.start_minutes)]
            top_concurrent = [item for item in concurrent if (item.artist_rank or 9999) <= 25]
            severe_top_conflicts = [item for item in top_concurrent if item.artist_slug != row.artist_slug and (item.artist_rank or 9999) <= 15]
            same_genre_conflicts = [item for item in concurrent if item.artist_slug != row.artist_slug and item.main_genre == row.main_genre]
            conflict = min(100.0, len(severe_top_conflicts) * 24 + len(same_genre_conflicts) * 7)
            row.conflict_score = round(conflict, 2)
            crowding_quality = 100 - min(100, row.crowding_score)
            conflict_quality = 100 - row.conflict_score
            experience_quality = row.experience_score
            row.optimization_score = round(
                normalize_score(
                    crowding_quality * config["crowding_weight"]
                    + conflict_quality * config["conflict_weight"]
                    + experience_quality * config["experience_weight"]
                ),
                2,
            )

    def _variant_summary(self, year: int, variant_key: str) -> OptimizedTimetableVariantSummary:
        """Build aggregate metrics for one variant."""
        rows = self._variant_rows(year, variant_key)
        config = VARIANT_CONFIGS[variant_key]
        slots_by_day = Counter(row.event_day for row in rows)
        slots_by_room = Counter(row.room_name for row in rows)
        generated_at = max((row.generated_at for row in rows if row.generated_at), default=None)
        changed = sum(1 for row in rows if row.original_room_slug != row.room_slug or row.original_start_minutes != row.start_minutes)
        return OptimizedTimetableVariantSummary(
            year=year,
            variant_key=variant_key,
            variant_name=config["name"],
            variant_description=config["description"],
            slot_count=len(rows),
            artist_count=len({row.artist_slug for row in rows}),
            room_count=len({row.room_slug for row in rows}),
            total_days=len({row.event_day for row in rows}),
            average_crowding_score=self._average([row.crowding_score for row in rows]),
            average_conflict_score=self._average([row.conflict_score for row in rows]),
            average_experience_score=self._average([row.experience_score for row in rows]),
            average_optimization_score=self._average([row.optimization_score for row in rows]),
            max_expected_pressure_score=round(max((row.expected_pressure_score for row in rows), default=0.0), 2),
            high_risk_slots=sum(1 for row in rows if row.crowd_risk in {"high", "extreme"}),
            changed_slots_from_probable=changed,
            rooms=sorted({row.room_name for row in rows}),
            slots_by_day={key: slots_by_day[key] for key in sorted(slots_by_day)},
            slots_by_room={key: slots_by_room[key] for key in sorted(slots_by_room)},
            model_version=MODEL_VERSION,
            method=MODEL_METHOD,
            solver_status=rows[0].solver_status if rows else self._solver_status(),
            generated_at=generated_at.replace(tzinfo=timezone.utc).isoformat() if generated_at else None,
            notes=["Lower crowding/conflict scores are better; higher experience/optimization scores are better."],
        )

    def _day_summaries(self, rows: list[V2OptimizedTimetableSlotModel]) -> list[OptimizedTimetableDaySummary]:
        """Build day-level metrics for a variant overview."""
        grouped: dict[str, list[V2OptimizedTimetableSlotModel]] = defaultdict(list)
        for row in rows:
            grouped[row.event_day].append(row)
        summaries = []
        for day, items in sorted(grouped.items()):
            ordered = sorted(items, key=lambda row: row.start_minutes)
            summaries.append(
                OptimizedTimetableDaySummary(
                    event_day=day,
                    festival_day=1 if day == "friday" else 2,
                    slot_count=len(items),
                    room_count=len({row.room_slug for row in items}),
                    first_start_time=ordered[0].start_time if ordered else None,
                    last_end_time=max(ordered, key=lambda row: row.end_minutes).end_time if ordered else None,
                    average_crowding_score=self._average([row.crowding_score for row in items]),
                    average_conflict_score=self._average([row.conflict_score for row in items]),
                    average_experience_score=self._average([row.experience_score for row in items]),
                )
            )
        return summaries

    def _row_to_slot(self, row: V2OptimizedTimetableSlotModel) -> OptimizedTimetableSlotRecord:
        """Convert one ORM row into the public schema."""
        generated_at = row.generated_at.replace(tzinfo=timezone.utc).isoformat() if row.generated_at else ""
        return OptimizedTimetableSlotRecord(
            id=row.id,
            year=row.year,
            variant_key=row.variant_key,
            variant_name=row.variant_name,
            variant_description=row.variant_description,
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
            crowding_score=round(row.crowding_score, 2),
            conflict_score=round(row.conflict_score, 2),
            experience_score=round(row.experience_score, 2),
            optimization_score=round(row.optimization_score, 2),
            crowd_risk=row.crowd_risk,
            original_room_slug=row.original_room_slug,
            original_start_minutes=row.original_start_minutes,
            changed_from_probable=row.original_room_slug != row.room_slug or row.original_start_minutes != row.start_minutes,
            probable_slot_id=row.probable_slot_id,
            model_version=row.model_version,
            method=row.method,
            solver_status=row.solver_status,
            official_status=row.official_status,
            source_status=row.source_status,
            is_official=row.is_official,
            reasons=[OptimizedTimetableReason(**item) for item in loads_json(row.reason_json, [])],
            constraints=[OptimizedTimetableConstraint(**item) for item in loads_json(row.constraint_json, [])],
            warnings=list(loads_json(row.warning_json, [])),
            generated_at=generated_at,
        )

    def _probable_rows(self, year: int) -> list[V2ProbableTimetableSlotModel]:
        """Return probable rows ordered by demand rank."""
        return list(
            self.db.scalars(
                select(V2ProbableTimetableSlotModel)
                .where(V2ProbableTimetableSlotModel.year == year)
                .order_by(V2ProbableTimetableSlotModel.artist_rank.asc().nullslast(), V2ProbableTimetableSlotModel.artist_slug.asc())
            ).all()
        )

    def _all_slots(self, year: int) -> list[V2OptimizedTimetableSlotModel]:
        """Return all optimized rows for a year."""
        return list(
            self.db.scalars(
                select(V2OptimizedTimetableSlotModel)
                .where(V2OptimizedTimetableSlotModel.year == year)
                .order_by(
                    V2OptimizedTimetableSlotModel.variant_key.asc(),
                    V2OptimizedTimetableSlotModel.event_day.asc(),
                    V2OptimizedTimetableSlotModel.room_slug.asc(),
                    V2OptimizedTimetableSlotModel.start_minutes.asc(),
                )
            ).all()
        )

    def _variant_rows(self, year: int, variant_key: str) -> list[V2OptimizedTimetableSlotModel]:
        """Return all rows for one variant."""
        return list(
            self.db.scalars(
                select(V2OptimizedTimetableSlotModel)
                .where(
                    V2OptimizedTimetableSlotModel.year == year,
                    V2OptimizedTimetableSlotModel.variant_key == variant_key,
                )
                .order_by(
                    V2OptimizedTimetableSlotModel.event_day.asc(),
                    V2OptimizedTimetableSlotModel.room_slug.asc(),
                    V2OptimizedTimetableSlotModel.start_minutes.asc(),
                )
            ).all()
        )

    def _ensure_optimized(self, year: int) -> None:
        """Generate variants lazily if the table is empty for a year."""
        existing = self.db.scalar(select(V2OptimizedTimetableSlotModel.id).where(V2OptimizedTimetableSlotModel.year == year).limit(1))
        if existing is None:
            self.rebuild(year, reset=True)

    def _artist_from_probable(self, row: V2ProbableTimetableSlotModel) -> ArtistPayload:
        """Extract artist payload from one V2.8 probable slot."""
        return ArtistPayload(
            source=row,
            artist_id=row.artist_id,
            artist_slug=row.artist_slug,
            artist_name=row.artist_name,
            artist_rank=row.artist_rank,
            show_name=row.show_name,
            performance_type=row.performance_type,
            main_genre=row.main_genre,
            secondary_genres_json=row.secondary_genres_json,
            popularity_score=row.popularity_score,
            career_score=row.career_score,
            momentum_score=row.momentum_score,
            nexus_affinity_score=row.nexus_affinity_score,
            demand_score=row.demand_score,
            crowd_risk=row.crowd_risk,
            original_room_slug=row.room_slug,
            original_start_minutes=row.start_minutes,
            probable_slot_id=row.id,
        )

    def _slot_from_probable(self, row: V2ProbableTimetableSlotModel) -> CandidateSlot:
        """Extract empty slot fields from one V2.8 probable slot."""
        return CandidateSlot(
            source=row,
            event_day=row.event_day,
            festival_day=row.festival_day,
            date_label=row.date_label,
            room_name=row.room_name,
            room_slug=row.room_slug,
            room_capacity=row.room_capacity,
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
        )


    def _reason_weight(self, value: float) -> float:
        """Clamp explanation weights to the public 0-100 schema range.

        Some internal optimization signals, especially capacity pressure, are
        allowed to exceed 100 to mark severe overcrowding risk. The API reason
        payload uses a normalized display weight instead, while the raw pressure
        still remains available in ``expected_pressure_score``.
        """
        return max(0.0, min(100.0, float(value)))

    def _expected_pressure(self, demand_score: float, capacity: int | None) -> float:
        """Estimate room pressure from demand and capacity. Values may exceed 100 before clipping."""
        safe_capacity = max(500, capacity or 1000)
        expected_people = 700 + demand_score * 38
        return round(min(140.0, (expected_people / safe_capacity) * 100), 2)

    def _crowd_risk_from_pressure(self, pressure: float) -> str:
        """Translate pressure score into a label."""
        if pressure >= 105:
            return "extreme"
        if pressure >= 88:
            return "high"
        if pressure >= 68:
            return "medium"
        return "low"

    def _genre_room_fit(self, genre: str, room_slug: str) -> float:
        """Return 0-100 fit for genre and room."""
        return float(GENRE_ROOM_PRIORS.get(genre, GENRE_ROOM_PRIORS["Unknown"]).get(room_slug, 52.0))

    def _normalize_room_slug(self, room: str) -> str:
        """Normalize canonical room names and known aliases to slugs."""
        value = room.strip().lower().replace("_", "-").replace(" ", "-")
        aliases = {
            "main": "main-room",
            "main-room": "main-room",
            "open-air": "open-air",
            "hangar": "hangar",
            "area-19": "area-19",
            "satelite": "satelite",
            "satellite": "satelite",
            "club": "club-area",
            "club-area": "club-area",
            "rave-area": "club-area",
            "rave-area-club": "club-area",
            "club-360": "club-area",
            "crystal": "crystal-area",
            "new-crystal": "crystal-area",
            "new-crystal-area": "crystal-area",
            "crystal-area": "crystal-area",
        }
        return aliases.get(value, value)

    def _average(self, values: list[float]) -> float:
        """Return rounded average for a numeric list."""
        return round(sum(values) / len(values), 2) if values else 0.0

    def _solver_status(self) -> str:
        """Return safe solver status for coverage before rows exist."""
        return "ortools_available" if cp_model is not None else "heuristic_fallback_no_ortools"
