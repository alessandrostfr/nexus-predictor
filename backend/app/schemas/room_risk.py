"""Schemas for room capacity, timetable and saturation risk.

Block 8 keeps the model honest: while the official 2026 timetable is missing,
all room pressure values are clearly marked as a theoretical simulation.
"""

from typing import Any

from pydantic import BaseModel, Field


class RoomMapPosition(BaseModel):
    """Normalized position used by the frontend SVG map."""

    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    width: float = Field(ge=0, le=100)
    height: float = Field(ge=0, le=100)


class RoomRiskArtist(BaseModel):
    """Artist that contributes to a theoretical room risk."""

    slug: str
    name: str
    main_genre: str = "Unknown"
    demand_score: float = 0
    crowd_risk: str = "unknown"
    rank: int | None = None


class RoomRiskFactor(BaseModel):
    """Human-readable factor used to explain room pressure."""

    key: str
    label: str
    value: float | int | str | None = None
    explanation: str


class RoomCapacityRisk(BaseModel):
    """One Fabrik room with capacity and room_pressure_score."""

    slug: str
    name: str
    area_type: str = "indoor"
    is_room: bool = True
    min_capacity: int | None = None
    estimated_capacity: int | None = None
    max_capacity: int | None = None
    capacity_confidence: str = "estimated"
    data_status: str = "theoretical_simulation"
    source_status: str = "capacity_seed_estimate"
    room_pressure_score: float = Field(ge=0, le=100)
    pressure_level: str
    pressure_percentage: float = Field(ge=0)
    simulated_expected_peak: int | None = None
    candidate_genres: list[str] = Field(default_factory=list)
    suggested_use: str | None = None
    top_candidate_artists: list[RoomRiskArtist] = Field(default_factory=list)
    factors: list[RoomRiskFactor] = Field(default_factory=list)
    map_position: RoomMapPosition
    notes: list[str] = Field(default_factory=list)


class VenueSupportArea(BaseModel):
    """Non-stage area shown on the map, such as the hotel."""

    slug: str
    name: str
    area_type: str
    is_room: bool = False
    map_position: RoomMapPosition
    notes: str


class TimetableSlot(BaseModel):
    """Future official timetable slot contract."""

    room_slug: str
    room_name: str
    start_time: str
    end_time: str
    artist_slugs: list[str] = Field(default_factory=list)
    artist_names: list[str] = Field(default_factory=list)
    source_status: str = "official_pending"


class RoomHeatmapCell(BaseModel):
    """Risk value for one room and time band."""

    room_slug: str
    room_name: str
    time_band: str
    label: str
    score: float = Field(ge=0, le=100)
    pressure_level: str
    data_status: str


class TimetableStatus(BaseModel):
    """Timetable import status and future import contract."""

    year: int
    official_available: bool
    source_status: str
    slots: list[TimetableSlot] = Field(default_factory=list)
    import_contract: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class RoomRiskOverview(BaseModel):
    """Full Block 8 response used by backend tests and frontend map."""

    year: int
    venue: str
    generated_at: str
    mode: str
    data_status: str
    official_timetable_available: bool
    rooms: list[RoomCapacityRisk]
    venue_support_areas: list[VenueSupportArea] = Field(default_factory=list)
    heatmap: list[RoomHeatmapCell] = Field(default_factory=list)
    timetable: TimetableStatus
    highest_risk_rooms: list[RoomCapacityRisk] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
