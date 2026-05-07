"""Schemas for V2.9 optimized 2026 timetable variants.

The generated rows are optimized scenarios, not an official Nexus/Fabrik
schedule. They are meant to compare three strategies: anti-crowding, balanced
and fan experience.
"""

from pydantic import BaseModel, Field


class OptimizedTimetableReason(BaseModel):
    """One explanation for an optimized slot decision."""

    key: str
    label: str
    weight: float = Field(ge=0, le=100)
    explanation: str


class OptimizedTimetableConstraint(BaseModel):
    """One optimization constraint or soft objective applied to a variant."""

    key: str
    label: str
    severity: str = "hard"
    satisfied: bool = True
    explanation: str


class OptimizedTimetableSlotRecord(BaseModel):
    """One optimized timetable assignment."""

    id: int | None = None
    year: int
    variant_key: str
    variant_name: str
    variant_description: str | None = None
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
    expected_pressure_score: float = Field(ge=0, le=140)
    crowding_score: float = Field(ge=0, le=100)
    conflict_score: float = Field(ge=0, le=100)
    experience_score: float = Field(ge=0, le=100)
    optimization_score: float = Field(ge=0, le=100)
    crowd_risk: str
    original_room_slug: str | None = None
    original_start_minutes: int | None = None
    changed_from_probable: bool = False
    probable_slot_id: int | None = None
    model_version: str
    method: str
    solver_status: str
    official_status: str = "optimized_not_official"
    source_status: str = "no_official_timetable_yet"
    is_official: bool = False
    reasons: list[OptimizedTimetableReason] = Field(default_factory=list)
    constraints: list[OptimizedTimetableConstraint] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    generated_at: str


class OptimizedTimetableSlotList(BaseModel):
    """Paginated optimized slot list."""

    year: int
    variant_key: str | None = None
    total: int
    limit: int
    offset: int
    items: list[OptimizedTimetableSlotRecord]


class OptimizedTimetableVariantSummary(BaseModel):
    """Variant-level metrics used by the comparison endpoint."""

    year: int
    variant_key: str
    variant_name: str
    variant_description: str
    slot_count: int
    artist_count: int
    room_count: int
    total_days: int
    average_crowding_score: float
    average_conflict_score: float
    average_experience_score: float
    average_optimization_score: float
    max_expected_pressure_score: float
    high_risk_slots: int
    changed_slots_from_probable: int
    rooms: list[str]
    slots_by_day: dict[str, int]
    slots_by_room: dict[str, int]
    model_version: str
    method: str
    solver_status: str
    generated_at: str | None = None
    notes: list[str] = Field(default_factory=list)


class OptimizedTimetableCoverage(BaseModel):
    """Coverage counters for all V2.9 variants."""

    year: int
    expected_variants: int
    generated_variants: int
    variant_keys: list[str]
    total_slots: int
    slots_per_variant: dict[str, int]
    assigned_artists_per_variant: dict[str, int]
    official_available: bool = False
    source_status: str = "no_official_timetable_yet"
    uses_ortools: bool
    model_version: str
    method: str
    generated_at: str | None = None


class OptimizedTimetableRebuildResult(BaseModel):
    """Result returned after rebuilding optimized timetable variants."""

    year: int
    model_version: str
    method: str
    solver_status: str
    variants: int
    variant_keys: list[str]
    slots: int
    assigned_artists_per_variant: dict[str, int]
    official_available: bool = False
    source_status: str = "no_official_timetable_yet"
    generated_at: str
    warnings: list[str] = Field(default_factory=list)


class OptimizedTimetableDaySummary(BaseModel):
    """Day-level optimized timetable summary."""

    event_day: str
    festival_day: int
    slot_count: int
    room_count: int
    first_start_time: str | None = None
    last_end_time: str | None = None
    average_crowding_score: float
    average_conflict_score: float
    average_experience_score: float


class OptimizedTimetableYearOverview(BaseModel):
    """Full overview for one optimized variant."""

    year: int
    variant: OptimizedTimetableVariantSummary
    days: list[OptimizedTimetableDaySummary]
    slots: list[OptimizedTimetableSlotRecord]
    notes: list[str] = Field(default_factory=list)


class OptimizedTimetableComparison(BaseModel):
    """Comparison payload for the three V2.9 variants."""

    year: int
    variants: list[OptimizedTimetableVariantSummary]
    recommended_by_goal: dict[str, str]
    metric_notes: list[str] = Field(default_factory=list)


class OptimizedTimetableOverlapIssue(BaseModel):
    """Overlap found inside one optimized variant/room/day."""

    year: int
    variant_key: str
    event_day: str
    room_slug: str
    first_artist: str
    first_start_time: str
    first_end_time: str
    second_artist: str
    second_start_time: str
    second_end_time: str


class OptimizedTimetableIntegrityReport(BaseModel):
    """Integrity report for optimized variants."""

    valid: bool
    official_available: bool = False
    source_status: str = "no_official_timetable_yet"
    expected_variants: int
    generated_variants: int
    missing_variants: list[str]
    incomplete_slots: int
    invalid_duration_slots: int
    overlap_count: int
    duplicate_artist_count: int
    invalid_room_count: int
    overlaps: list[OptimizedTimetableOverlapIssue] = Field(default_factory=list)
    rooms_used: list[str]
    is_seven_room_fabrik_model: bool
    notes: list[str] = Field(default_factory=list)
