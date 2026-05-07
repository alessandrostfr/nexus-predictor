"""Schemas for V2.6 historical timetable slots.

The historical timetable API is intentionally data-quality oriented. It exposes
room aliases, confidence, extraction method and integrity checks because the
source material comes from images/manual transcription and must remain auditable.
"""

from pydantic import BaseModel, Field


class HistoricalTimetableSlotRecord(BaseModel):
    """One normalized set in a historical Nexus timetable."""

    id: int | None = None
    year: int
    event_day: str
    festival_day: int
    date_label: str | None = None
    room_name: str
    room_slug: str
    observed_room_name: str | None = None
    room_aliases: list[str] = Field(default_factory=list)
    artist_slug: str | None = None
    artist_name: str
    show_name: str
    performance_type: str = "solo"
    start_time: str
    end_time: str
    start_minutes: int
    end_minutes: int
    duration_minutes: int
    slot_order: int
    slot_type: str = "standard"
    is_headliner_slot: bool = False
    is_closing_slot: bool = False
    is_warmup_slot: bool = False
    is_special_show: bool = False
    source_name: str
    source_url: str | None = None
    confidence: str = "medium"
    extraction_method: str = "manual_image_transcription"
    status: str = "pending_review"
    notes: str | None = None


class HistoricalTimetableSlotList(BaseModel):
    """Paginated list of normalized slots."""

    total: int
    limit: int
    offset: int
    items: list[HistoricalTimetableSlotRecord]


class HistoricalRoomSummary(BaseModel):
    """Room coverage summary for one historical year/day."""

    year: int
    event_day: str | None = None
    room_name: str
    room_slug: str
    observed_aliases: list[str] = Field(default_factory=list)
    slot_count: int
    first_start_time: str | None = None
    last_end_time: str | None = None
    headliner_slots: int = 0


class HistoricalTimetableDaySummary(BaseModel):
    """Summary for one festival day inside a year."""

    event_day: str
    festival_day: int
    date_label: str | None = None
    slot_count: int
    room_count: int
    first_start_time: str | None = None
    last_end_time: str | None = None


class HistoricalTimetableYearOverview(BaseModel):
    """Aggregated historical timetable overview for one year."""

    year: int
    slot_count: int
    room_count: int
    rooms: list[HistoricalRoomSummary]
    days: list[HistoricalTimetableDaySummary]
    headliner_slots: int
    warmup_slots: int
    closing_slots: int
    special_show_slots: int
    confidence_breakdown: dict[str, int] = Field(default_factory=dict)


class HistoricalTimetableCoverage(BaseModel):
    """Global V2.6 coverage and quality indicators."""

    years: list[int]
    total_slots: int
    total_days: int
    total_rooms: int
    slots_by_year: dict[str, int]
    days_by_year: dict[str, int]
    rooms_by_year: dict[str, int]
    slots_with_artist_slug: int
    slots_with_source: int
    headliner_slots: int
    warmup_slots: int
    closing_slots: int
    special_show_slots: int
    incomplete_slots: int
    overlap_count: int
    year_2025_room_count: int
    year_2025_rooms: list[str]
    year_2025_is_seven_room_model: bool


class HistoricalTimetableImportResult(BaseModel):
    """Result returned after importing the V2.6 historical timetable seed."""

    sources: int
    slots: int
    evidence_items: int
    artist_metrics: int
    years: list[int]
    year_2025_room_count: int
    coverage: HistoricalTimetableCoverage


class HistoricalTimetableOverlapIssue(BaseModel):
    """Potential overlap inside one room/day."""

    year: int
    event_day: str
    room_slug: str
    first_artist: str
    first_start_time: str
    first_end_time: str
    second_artist: str
    second_start_time: str
    second_end_time: str


class HistoricalTimetableIntegrityReport(BaseModel):
    """Data integrity report for the historical timetable table."""

    valid: bool
    incomplete_slots: int
    invalid_duration_slots: int
    overlap_count: int
    overlaps: list[HistoricalTimetableOverlapIssue] = Field(default_factory=list)
    year_2025_room_count: int
    year_2025_rooms: list[str]
    year_2025_is_seven_room_model: bool
    notes: list[str] = Field(default_factory=list)
