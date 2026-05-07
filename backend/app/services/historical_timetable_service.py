"""V2.6 historical timetable import and query service.

The service loads the editable JSON seed created from historical timetable
images/manual transcription, normalizes room aliases and persists every slot to
PostgreSQL. The goal is not only to list sets, but to give later prediction and
optimization blocks reliable signals: room, day, time, headliner/closing/warm-up
flags and confidence/source metadata.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any

from slugify import slugify
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.paths import HISTORICAL_TIMETABLES_PATH
from app.db.models import ArtistMetricModel, ArtistModel, EvidenceItemModel, HistoricalTimetableSlotModel, SourceModel
from app.schemas.historical_timetable import (
    HistoricalRoomSummary,
    HistoricalTimetableCoverage,
    HistoricalTimetableDaySummary,
    HistoricalTimetableImportResult,
    HistoricalTimetableIntegrityReport,
    HistoricalTimetableOverlapIssue,
    HistoricalTimetableSlotList,
    HistoricalTimetableSlotRecord,
    HistoricalTimetableYearOverview,
)
from app.services.database_seed_service import dumps_json, ensure_database_ready, loads_json
from app.services.evidence_seed_service import create_evidence, get_or_create_source, normalize_confidence, upsert_artist_metric

TIMETABLE_SLOT_METRIC = "timetable.historical_slot"
TIMETABLE_METRIC_PREFIX = "historical_timetable."

# Canonical room map. V2.6 keeps aliases visible because 2024/2025 images can
# label the same physical room differently.
ROOM_CANONICAL_ALIASES: dict[str, dict[str, Any]] = {
    "main-room": {
        "name": "Main Room",
        "aliases": ["Main", "Main Room", "Fabrik Main", "Main Stage"],
    },
    "hangar": {
        "name": "Hangar",
        "aliases": ["Hangar", "El Hangar", "The Hangar"],
    },
    "open-air": {
        "name": "Open Air",
        "aliases": ["Open Air", "Openair", "Open-Air", "Outdoor"],
    },
    "satelite": {
        "name": "Satelite",
        "aliases": ["Satelite", "Satellite", "Satélite"],
    },
    "club-area": {
        "name": "Club Area",
        "aliases": ["Club Area", "Rave Area Club", "Rave Area", "Club 360", "Club"],
    },
    "crystal-area": {
        "name": "Crystal Area",
        "aliases": ["Crystal Area", "New Crystal", "Crystal", "New Crystal Area"],
    },
    "area-19": {
        "name": "Area 19",
        "aliases": ["Area 19", "Area19", "Área 19"],
    },
}

CANONICAL_BY_ALIAS = {
    alias.lower().strip(): slug
    for slug, payload in ROOM_CANONICAL_ALIASES.items()
    for alias in [payload["name"], *payload["aliases"]]
}


def minutes_to_time(value: int) -> str:
    """Convert absolute event minutes into a wrapped HH:MM string."""
    wrapped = value % (24 * 60)
    return f"{wrapped // 60:02d}:{wrapped % 60:02d}"


def parse_time_to_minutes(value: str) -> int:
    """Parse HH:MM and place after-midnight times in the same event night."""
    hour, minute = [int(part) for part in value.split(":", maxsplit=1)]
    total = hour * 60 + minute
    # Nexus runs through the night. Values before noon belong to the following
    # event day so overlap checks can compare them linearly.
    if hour < 12:
        total += 24 * 60
    return total


class HistoricalTimetableService:
    """Import, validate and query V2.6 historical timetable data."""

    def __init__(self, db: Session) -> None:
        """Keep a request-scoped database session and ensure V1 seeds exist."""
        self.db = db
        ensure_database_ready(self.db)

    def import_seed(self, *, reset: bool = True) -> HistoricalTimetableImportResult:
        """Import the editable historical timetable JSON into PostgreSQL."""
        payload = self._load_payload()
        if reset:
            self._reset_historical_timetables()

        sources = self._upsert_sources(payload.get("sources", []))
        artists_by_slug = {artist.slug: artist for artist in self.db.scalars(select(ArtistModel)).all()}
        inserted_slots = 0
        evidence_items = 0
        artist_slot_counter: Counter[str] = Counter()
        artist_headliner_counter: Counter[str] = Counter()

        for raw_slot in payload.get("slots", []):
            normalized = self._normalize_raw_slot(raw_slot)
            source = sources[normalized["source_key"]]
            artist = artists_by_slug.get(normalized["artist_slug"] or "")

            evidence = create_evidence(
                self.db,
                artist=artist,
                source=source,
                metric_key=TIMETABLE_SLOT_METRIC,
                metric_value={
                    "year": normalized["year"],
                    "event_day": normalized["event_day"],
                    "room": normalized["room_name"],
                    "artist": normalized["artist_name"],
                    "show": normalized["show_name"],
                    "start_time": normalized["start_time"],
                    "end_time": normalized["end_time"],
                    "slot_type": normalized["slot_type"],
                },
                value_type="json",
                confidence=normalized["confidence"],
                extraction_method=normalized["extraction_method"],
                evidence_kind="historical_timetable_slot",
                status=normalized["status"],
                notes=normalized["notes"],
                source_url=normalized["source_url"],
                raw=normalized,
            )
            evidence_items += 1

            slot = HistoricalTimetableSlotModel(
                year=normalized["year"],
                event_day=normalized["event_day"],
                festival_day=normalized["festival_day"],
                date_label=normalized["date_label"],
                room_name=normalized["room_name"],
                room_slug=normalized["room_slug"],
                observed_room_name=normalized["observed_room_name"],
                room_aliases_json=dumps_json(normalized["room_aliases"]),
                artist_id=artist.id if artist else None,
                artist_slug=normalized["artist_slug"],
                artist_name=normalized["artist_name"],
                show_name=normalized["show_name"],
                performance_type=normalized["performance_type"],
                start_time=normalized["start_time"],
                end_time=normalized["end_time"],
                start_minutes=normalized["start_minutes"],
                end_minutes=normalized["end_minutes"],
                duration_minutes=normalized["duration_minutes"],
                slot_order=normalized["slot_order"],
                slot_type=normalized["slot_type"],
                is_headliner_slot=normalized["is_headliner_slot"],
                is_closing_slot=normalized["is_closing_slot"],
                is_warmup_slot=normalized["is_warmup_slot"],
                is_special_show=normalized["is_special_show"],
                source_name=source.name,
                source_url=normalized["source_url"],
                source_id=source.id,
                evidence_id=evidence.id,
                confidence=normalized["confidence"],
                extraction_method=normalized["extraction_method"],
                status=normalized["status"],
                notes=normalized["notes"],
                raw_json=dumps_json(normalized),
            )
            self.db.add(slot)
            inserted_slots += 1

            if artist:
                artist_slot_counter[artist.slug] += 1
                if normalized["is_headliner_slot"]:
                    artist_headliner_counter[artist.slug] += 1

        self.db.flush()
        inserted_metrics = self._upsert_artist_timetable_metrics(
            artists_by_slug=artists_by_slug,
            artist_slot_counter=artist_slot_counter,
            artist_headliner_counter=artist_headliner_counter,
        )
        self.db.commit()

        coverage = self.coverage()
        return HistoricalTimetableImportResult(
            sources=len(sources),
            slots=inserted_slots,
            evidence_items=evidence_items,
            artist_metrics=inserted_metrics,
            years=coverage.years,
            year_2025_room_count=coverage.year_2025_room_count,
            coverage=coverage,
        )

    def coverage(self) -> HistoricalTimetableCoverage:
        """Return global V2.6 coverage and quality counters."""
        slots = self._all_slots()
        years = sorted({slot.year for slot in slots})
        slots_by_year: Counter[int] = Counter(slot.year for slot in slots)
        days_by_year: dict[int, set[str]] = defaultdict(set)
        rooms_by_year: dict[int, set[str]] = defaultdict(set)
        rooms_all: set[str] = set()

        for slot in slots:
            days_by_year[slot.year].add(slot.event_day)
            rooms_by_year[slot.year].add(slot.room_name)
            rooms_all.add(slot.room_name)

        integrity = self.integrity_report(max_overlaps=1000)
        year_2025_rooms = sorted(rooms_by_year.get(2025, set()))
        return HistoricalTimetableCoverage(
            years=years,
            total_slots=len(slots),
            total_days=sum(len(days) for days in days_by_year.values()),
            total_rooms=len(rooms_all),
            slots_by_year={str(year): slots_by_year[year] for year in years},
            days_by_year={str(year): len(days_by_year[year]) for year in years},
            rooms_by_year={str(year): len(rooms_by_year[year]) for year in years},
            slots_with_artist_slug=sum(1 for slot in slots if slot.artist_slug),
            slots_with_source=sum(1 for slot in slots if slot.source_name),
            headliner_slots=sum(1 for slot in slots if slot.is_headliner_slot),
            warmup_slots=sum(1 for slot in slots if slot.is_warmup_slot),
            closing_slots=sum(1 for slot in slots if slot.is_closing_slot),
            special_show_slots=sum(1 for slot in slots if slot.is_special_show),
            incomplete_slots=integrity.incomplete_slots,
            overlap_count=integrity.overlap_count,
            year_2025_room_count=len(year_2025_rooms),
            year_2025_rooms=year_2025_rooms,
            year_2025_is_seven_room_model=len(year_2025_rooms) == 7,
        )

    def list_slots(
        self,
        *,
        year: int | None = None,
        event_day: str | None = None,
        room: str | None = None,
        artist_slug: str | None = None,
        only_headliners: bool = False,
        limit: int = 200,
        offset: int = 0,
    ) -> HistoricalTimetableSlotList:
        """Return historical slots with common filters."""
        statement = select(HistoricalTimetableSlotModel)
        if year is not None:
            statement = statement.where(HistoricalTimetableSlotModel.year == year)
        if event_day:
            statement = statement.where(HistoricalTimetableSlotModel.event_day == event_day)
        if room:
            room_slug = self.normalize_room(room)["slug"]
            statement = statement.where(HistoricalTimetableSlotModel.room_slug == room_slug)
        if artist_slug:
            statement = statement.where(HistoricalTimetableSlotModel.artist_slug == artist_slug)
        if only_headliners:
            statement = statement.where(HistoricalTimetableSlotModel.is_headliner_slot.is_(True))

        ordered = statement.order_by(
            HistoricalTimetableSlotModel.year,
            HistoricalTimetableSlotModel.festival_day,
            HistoricalTimetableSlotModel.room_slug,
            HistoricalTimetableSlotModel.start_minutes,
        )
        total = self.db.scalar(select(func.count()).select_from(ordered.subquery())) or 0
        rows = list(self.db.scalars(ordered.limit(limit).offset(offset)))
        return HistoricalTimetableSlotList(
            total=total,
            limit=limit,
            offset=offset,
            items=[self._slot_to_schema(slot) for slot in rows],
        )

    def year_overview(self, year: int) -> HistoricalTimetableYearOverview | None:
        """Return days, rooms and quality indicators for one historical year."""
        slots = self._all_slots(year=year)
        if not slots:
            return None

        room_summaries = self._room_summaries(slots)
        day_summaries = self._day_summaries(slots)
        confidence_breakdown = Counter(slot.confidence for slot in slots)
        return HistoricalTimetableYearOverview(
            year=year,
            slot_count=len(slots),
            room_count=len({slot.room_slug for slot in slots}),
            rooms=room_summaries,
            days=day_summaries,
            headliner_slots=sum(1 for slot in slots if slot.is_headliner_slot),
            warmup_slots=sum(1 for slot in slots if slot.is_warmup_slot),
            closing_slots=sum(1 for slot in slots if slot.is_closing_slot),
            special_show_slots=sum(1 for slot in slots if slot.is_special_show),
            confidence_breakdown=dict(confidence_breakdown),
        )

    def rooms_for_year(self, year: int, event_day: str | None = None) -> list[HistoricalRoomSummary]:
        """Return room coverage for one year, optionally scoped to one day."""
        slots = self._all_slots(year=year)
        if event_day:
            slots = [slot for slot in slots if slot.event_day == event_day]
        return self._room_summaries(slots)

    def integrity_report(self, *, max_overlaps: int = 50) -> HistoricalTimetableIntegrityReport:
        """Detect incomplete slots, invalid durations and room/day overlaps."""
        slots = self._all_slots()
        incomplete = [slot for slot in slots if not slot.room_slug or not slot.artist_name or not slot.start_time or not slot.end_time]
        invalid_duration = [slot for slot in slots if slot.duration_minutes <= 0 or slot.end_minutes <= slot.start_minutes]
        overlaps = self._find_overlaps(slots)
        year_2025_rooms = sorted({slot.room_name for slot in slots if slot.year == 2025})
        notes: list[str] = []
        if len(year_2025_rooms) == 7:
            notes.append("2025 is normalized to the verified seven-room Fabrik model.")
        else:
            notes.append("2025 room count does not match the expected seven-room model.")
        if overlaps:
            notes.append("Potential overlaps found inside at least one room/day.")
        if incomplete or invalid_duration:
            notes.append("Some slots are incomplete or have invalid durations.")

        return HistoricalTimetableIntegrityReport(
            valid=not incomplete and not invalid_duration and not overlaps and len(year_2025_rooms) == 7,
            incomplete_slots=len(incomplete),
            invalid_duration_slots=len(invalid_duration),
            overlap_count=len(overlaps),
            overlaps=overlaps[:max_overlaps],
            year_2025_room_count=len(year_2025_rooms),
            year_2025_rooms=year_2025_rooms,
            year_2025_is_seven_room_model=len(year_2025_rooms) == 7,
            notes=notes,
        )

    def normalize_room(self, room_name: str) -> dict[str, Any]:
        """Normalize any historical room alias into a canonical room payload."""
        cleaned = room_name.strip()
        slug = CANONICAL_BY_ALIAS.get(cleaned.lower()) or slugify(cleaned)
        payload = ROOM_CANONICAL_ALIASES.get(slug, {"name": cleaned, "aliases": [cleaned]})
        return {"slug": slug, "name": payload["name"], "aliases": sorted(set(payload["aliases"]))}

    def _load_payload(self) -> dict[str, Any]:
        """Read the historical timetable seed from disk."""
        if not HISTORICAL_TIMETABLES_PATH.exists():
            raise FileNotFoundError(f"Missing historical timetable seed: {HISTORICAL_TIMETABLES_PATH}")
        return json.loads(HISTORICAL_TIMETABLES_PATH.read_text(encoding="utf-8"))

    def _upsert_sources(self, sources_payload: list[dict[str, Any]]) -> dict[str, SourceModel]:
        """Create or update source registry entries declared by the seed."""
        sources: dict[str, SourceModel] = {}
        for item in sources_payload:
            key = item["key"]
            sources[key] = get_or_create_source(
                self.db,
                key=key,
                name=item.get("name", key),
                source_type=item.get("source_type", "manual_evidence"),
                base_url=item.get("url"),
                confidence=item.get("confidence", "medium"),
                extraction_method=item.get("extraction_method", "manual_image_transcription"),
                notes=item.get("notes"),
                raw=item,
            )
        return sources

    def _reset_historical_timetables(self) -> None:
        """Delete only V2.6 rows/evidence/metrics, preserving previous blocks."""
        self.db.execute(delete(HistoricalTimetableSlotModel))
        self.db.execute(delete(EvidenceItemModel).where(EvidenceItemModel.metric_key == TIMETABLE_SLOT_METRIC))
        self.db.execute(delete(ArtistMetricModel).where(ArtistMetricModel.metric_key.like(f"{TIMETABLE_METRIC_PREFIX}%")))
        self.db.flush()

    def _normalize_raw_slot(self, raw_slot: dict[str, Any]) -> dict[str, Any]:
        """Convert a JSON slot into DB-ready fields."""
        room = self.normalize_room(raw_slot["room"])
        start_minutes = raw_slot.get("start_minutes") or parse_time_to_minutes(raw_slot["start_time"])
        end_minutes = raw_slot.get("end_minutes") or parse_time_to_minutes(raw_slot["end_time"])
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60
        duration = end_minutes - start_minutes
        performance_type = raw_slot.get("performance_type", "solo")
        is_special_show = bool(raw_slot.get("is_special_show")) or performance_type in {
            "b2b",
            "versus",
            "collaboration",
            "special_show",
            "live",
            "showcase",
        }
        is_headliner = bool(raw_slot.get("is_headliner_slot"))
        is_closing = bool(raw_slot.get("is_closing_slot"))
        is_warmup = bool(raw_slot.get("is_warmup_slot"))
        slot_type = raw_slot.get("slot_type") or (
            "headliner" if is_headliner else "closing" if is_closing else "warm_up" if is_warmup else "special_show" if is_special_show else "standard"
        )
        return {
            "year": int(raw_slot["year"]),
            "event_day": raw_slot["event_day"],
            "festival_day": int(raw_slot.get("festival_day", 1)),
            "date_label": raw_slot.get("date_label"),
            "room_name": room["name"],
            "room_slug": room["slug"],
            "observed_room_name": raw_slot.get("observed_room_name") or raw_slot["room"],
            "room_aliases": room["aliases"],
            "artist_slug": raw_slot.get("artist_slug"),
            "artist_name": raw_slot.get("artist_name") or raw_slot.get("show_name") or "Unknown artist",
            "show_name": raw_slot.get("show_name") or raw_slot.get("artist_name") or "Unknown show",
            "performance_type": performance_type,
            "start_time": minutes_to_time(start_minutes),
            "end_time": minutes_to_time(end_minutes),
            "start_minutes": int(start_minutes),
            "end_minutes": int(end_minutes),
            "duration_minutes": int(duration),
            "slot_order": int(raw_slot.get("slot_order", 0)),
            "slot_type": slot_type,
            "is_headliner_slot": is_headliner,
            "is_closing_slot": is_closing,
            "is_warmup_slot": is_warmup,
            "is_special_show": is_special_show,
            "source_key": raw_slot.get("source_key", f"historical_timetable_{raw_slot['year']}"),
            "source_url": raw_slot.get("source_url"),
            "confidence": normalize_confidence(raw_slot.get("confidence", "medium")),
            "extraction_method": raw_slot.get("extraction_method", "manual_image_transcription"),
            "status": raw_slot.get("status", "pending_review"),
            "notes": raw_slot.get("notes"),
        }

    def _upsert_artist_timetable_metrics(
        self,
        *,
        artists_by_slug: dict[str, ArtistModel],
        artist_slot_counter: Counter[str],
        artist_headliner_counter: Counter[str],
    ) -> int:
        """Store artist-level timetable features for V2.7+ model work."""
        inserted = 0
        for slug, count in artist_slot_counter.items():
            artist = artists_by_slug.get(slug)
            if not artist:
                continue
            upsert_artist_metric(
                self.db,
                artist=artist,
                metric_key=f"{TIMETABLE_METRIC_PREFIX}slot_count",
                numeric_value=float(count),
                value_type="number",
                confidence="medium",
                evidence_count=count,
                notes="Number of normalized historical timetable slots for this artist.",
                raw={"source": "v2.6_historical_timetable_import"},
            )
            inserted += 1
            upsert_artist_metric(
                self.db,
                artist=artist,
                metric_key=f"{TIMETABLE_METRIC_PREFIX}headliner_slot_count",
                numeric_value=float(artist_headliner_counter.get(slug, 0)),
                value_type="number",
                confidence="medium",
                evidence_count=artist_headliner_counter.get(slug, 0),
                notes="Number of normalized historical headliner slots for this artist.",
                raw={"source": "v2.6_historical_timetable_import"},
            )
            inserted += 1
        return inserted

    def _all_slots(self, *, year: int | None = None) -> list[HistoricalTimetableSlotModel]:
        """Load slots ordered for deterministic validation and API output."""
        statement = select(HistoricalTimetableSlotModel)
        if year is not None:
            statement = statement.where(HistoricalTimetableSlotModel.year == year)
        statement = statement.order_by(
            HistoricalTimetableSlotModel.year,
            HistoricalTimetableSlotModel.festival_day,
            HistoricalTimetableSlotModel.room_slug,
            HistoricalTimetableSlotModel.start_minutes,
        )
        return list(self.db.scalars(statement))

    def _slot_to_schema(self, slot: HistoricalTimetableSlotModel) -> HistoricalTimetableSlotRecord:
        """Convert an ORM slot to a public schema."""
        return HistoricalTimetableSlotRecord(
            id=slot.id,
            year=slot.year,
            event_day=slot.event_day,
            festival_day=slot.festival_day,
            date_label=slot.date_label,
            room_name=slot.room_name,
            room_slug=slot.room_slug,
            observed_room_name=slot.observed_room_name,
            room_aliases=loads_json(slot.room_aliases_json, fallback=[]),
            artist_slug=slot.artist_slug,
            artist_name=slot.artist_name,
            show_name=slot.show_name,
            performance_type=slot.performance_type,
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
            source_name=slot.source_name,
            source_url=slot.source_url,
            confidence=slot.confidence,
            extraction_method=slot.extraction_method,
            status=slot.status,
            notes=slot.notes,
        )

    def _room_summaries(self, slots: list[HistoricalTimetableSlotModel]) -> list[HistoricalRoomSummary]:
        """Build deterministic room summaries from slot rows."""
        grouped: dict[tuple[int, str, str], list[HistoricalTimetableSlotModel]] = defaultdict(list)
        for slot in slots:
            grouped[(slot.year, slot.event_day, slot.room_slug)].append(slot)

        summaries: list[HistoricalRoomSummary] = []
        for (year, event_day, room_slug), rows in sorted(grouped.items()):
            rows.sort(key=lambda row: row.start_minutes)
            aliases = sorted({row.observed_room_name for row in rows if row.observed_room_name})
            summaries.append(
                HistoricalRoomSummary(
                    year=year,
                    event_day=event_day,
                    room_name=rows[0].room_name,
                    room_slug=room_slug,
                    observed_aliases=aliases,
                    slot_count=len(rows),
                    first_start_time=rows[0].start_time,
                    last_end_time=rows[-1].end_time,
                    headliner_slots=sum(1 for row in rows if row.is_headliner_slot),
                )
            )
        return summaries

    def _day_summaries(self, slots: list[HistoricalTimetableSlotModel]) -> list[HistoricalTimetableDaySummary]:
        """Build day summaries from slot rows."""
        grouped: dict[str, list[HistoricalTimetableSlotModel]] = defaultdict(list)
        for slot in slots:
            grouped[slot.event_day].append(slot)

        summaries: list[HistoricalTimetableDaySummary] = []
        for event_day, rows in sorted(grouped.items(), key=lambda item: min(row.festival_day for row in item[1])):
            rows.sort(key=lambda row: row.start_minutes)
            summaries.append(
                HistoricalTimetableDaySummary(
                    event_day=event_day,
                    festival_day=min(row.festival_day for row in rows),
                    date_label=rows[0].date_label,
                    slot_count=len(rows),
                    room_count=len({row.room_slug for row in rows}),
                    first_start_time=rows[0].start_time,
                    last_end_time=max(rows, key=lambda row: row.end_minutes).end_time,
                )
            )
        return summaries

    def _find_overlaps(self, slots: list[HistoricalTimetableSlotModel]) -> list[HistoricalTimetableOverlapIssue]:
        """Find overlapping slots inside the same year/day/room."""
        grouped: dict[tuple[int, str, str], list[HistoricalTimetableSlotModel]] = defaultdict(list)
        for slot in slots:
            grouped[(slot.year, slot.event_day, slot.room_slug)].append(slot)

        issues: list[HistoricalTimetableOverlapIssue] = []
        for (year, event_day, room_slug), rows in grouped.items():
            rows.sort(key=lambda row: row.start_minutes)
            for previous, current in zip(rows, rows[1:]):
                if current.start_minutes < previous.end_minutes:
                    issues.append(
                        HistoricalTimetableOverlapIssue(
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
        return issues
