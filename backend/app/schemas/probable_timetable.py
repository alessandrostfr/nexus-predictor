"""Schemas for V2.8 probable 2026 timetable predictions.

The official 2026 Nexus timetable is not available yet. These schemas therefore
make the prediction status explicit in every public payload: rows are inferred,
not official, and each slot carries confidence plus human-readable reasons.
"""

from pydantic import BaseModel, Field


class ProbableTimetableReason(BaseModel):
    """One reason that explains a room/time assignment."""

    key: str
    label: str
    weight: float = Field(ge=0, le=100)
    explanation: str


class ProbableTimetableSlotRecord(BaseModel):
    """One predicted timetable slot for Nexus 2026."""

    id: int | None = None
    year: int
    timetable_kind: str = "probable"
    event_day: str
    festival_day: int
    date_label: str | None = None
    room_name: str
    room_slug: str
    room_capacity: int | None = None
    artist_slug: str
    artist_name: str
    artist_rank: int | None = None
    show_name: str
    performance_type: str = "solo"
    main_genre: str = "Unknown"
    secondary_genres: list[str] = Field(default_factory=list)
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
    popularity_score: float = Field(ge=0, le=100)
    career_score: float = Field(ge=0, le=100)
    momentum_score: float = Field(ge=0, le=100)
    nexus_affinity_score: float = Field(ge=0, le=100)
    demand_score: float = Field(ge=0, le=100)
    expected_pressure_score: float = Field(ge=0, le=100)
    probability_score: float = Field(ge=0, le=100)
    crowd_risk: str
    confidence: str
    model_version: str
    method: str
    official_status: str = "predicted_not_official"
    source_status: str = "no_official_timetable_yet"
    is_official: bool = False
    reasons: list[ProbableTimetableReason] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    historical_pattern: dict[str, object] = Field(default_factory=dict)
    generated_at: str


class ProbableTimetableSlotList(BaseModel):
    """Paginated probable timetable slot list."""

    year: int
    total: int
    limit: int
    offset: int
    items: list[ProbableTimetableSlotRecord]


class ProbableTimetableRoomSummary(BaseModel):
    """Predicted room usage summary for one day or whole timetable."""

    year: int
    event_day: str | None = None
    room_name: str
    room_slug: str
    room_capacity: int | None = None
    slot_count: int
    first_start_time: str | None = None
    last_end_time: str | None = None
    average_demand_score: float
    max_expected_pressure_score: float
    headliner_slots: int = 0
    confidence_breakdown: dict[str, int] = Field(default_factory=dict)


class ProbableTimetableDaySummary(BaseModel):
    """Predicted day-level summary."""

    event_day: str
    festival_day: int
    date_label: str | None = None
    slot_count: int
    room_count: int
    first_start_time: str | None = None
    last_end_time: str | None = None
    average_demand_score: float
    max_expected_pressure_score: float


class ProbableTimetableCoverage(BaseModel):
    """Coverage and quality counters for V2.8."""

    year: int
    timetable_kind: str = "probable"
    official_available: bool = False
    source_status: str = "no_official_timetable_yet"
    total_slots: int
    total_artists: int
    assigned_artists: int
    unassigned_artists: int
    total_days: int
    total_rooms: int
    rooms: list[str]
    slots_by_day: dict[str, int]
    slots_by_room: dict[str, int]
    headliner_slots: int
    warmup_slots: int
    closing_slots: int
    average_probability_score: float
    average_confidence_score: float
    confidence_breakdown: dict[str, int]
    model_version: str
    method: str
    generated_at: str | None = None


class ProbableTimetableYearOverview(BaseModel):
    """Full overview for the probable 2026 timetable."""

    year: int
    timetable_kind: str = "probable"
    official_available: bool = False
    official_status: str = "predicted_not_official"
    source_status: str = "no_official_timetable_yet"
    slot_count: int
    artist_count: int
    room_count: int
    rooms: list[ProbableTimetableRoomSummary]
    days: list[ProbableTimetableDaySummary]
    headliner_slots: int
    warmup_slots: int
    closing_slots: int
    confidence_breakdown: dict[str, int] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class ProbableTimetableRebuildResult(BaseModel):
    """Result returned after rebuilding the probable timetable."""

    year: int
    model_version: str
    method: str
    slots: int
    assigned_artists: int
    unassigned_artists: int
    rooms_used: int
    official_available: bool = False
    source_status: str = "no_official_timetable_yet"
    generated_at: str
    warnings: list[str] = Field(default_factory=list)


class ProbableTimetableOverlapIssue(BaseModel):
    """Overlap found inside the same predicted room/day."""

    year: int
    event_day: str
    room_slug: str
    first_artist: str
    first_start_time: str
    first_end_time: str
    second_artist: str
    second_start_time: str
    second_end_time: str


class ProbableTimetableIntegrityReport(BaseModel):
    """Integrity report for V2.8 probable timetable output."""

    valid: bool
    official_available: bool = False
    source_status: str = "no_official_timetable_yet"
    incomplete_slots: int
    invalid_duration_slots: int
    overlap_count: int
    duplicate_artist_count: int
    invalid_room_count: int
    capacity_pressure_violations: int
    overlaps: list[ProbableTimetableOverlapIssue] = Field(default_factory=list)
    rooms_used: list[str]
    is_seven_room_fabrik_model: bool
    notes: list[str] = Field(default_factory=list)
