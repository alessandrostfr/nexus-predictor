"""Schemas for V3.1 continuous event contracts.

The event contract is a data contract, not a prediction. It tells every future
pipeline, feature builder and timetable view how the 2026 event exists in time.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class EventTimeWindowRecord(BaseModel):
    """One hourly window inside the continuous Nexus 2026 event."""

    id: int | None = None
    year: int
    window_index: int
    window_key: str
    label: str
    starts_at: datetime
    ends_at: datetime
    start_time: str
    end_time: str
    start_minutes_from_event_start: int
    end_minutes_from_event_start: int
    duration_minutes: int = 60
    crosses_midnight: bool = False
    functional_day_key: str = "nexus_day"
    slot_type: str = "standard"
    is_peak_window: bool = False
    evidence_status: str = "contract_window"
    confidence: str = "high"
    notes: str | None = None


class EventContractRecord(BaseModel):
    """Readable event contract with all continuous time windows."""

    id: int | None = None
    year: int
    event_key: str
    name: str
    event_type: str = "festival"
    venue: str
    city: str | None = None
    timezone: str = "Europe/Madrid"
    starts_at: datetime
    ends_at: datetime
    start_label: str
    end_label: str
    duration_hours: int
    duration_minutes: int
    continuous_event: bool
    functional_day_key: str = "nexus_day"
    visible_label: str
    source_status: str
    confidence: str
    extraction_method: str
    boundary_labels: list[str] = Field(default_factory=list)
    peak_windows: list[dict[str, object]] = Field(default_factory=list)
    time_windows: list[EventTimeWindowRecord] = Field(default_factory=list)
    notes: str | None = None


class EventContractRebuildResult(BaseModel):
    """Result returned after rebuilding one event contract."""

    year: int
    event_key: str
    duration_hours: int
    time_windows: int
    continuous_event: bool
    start_label: str
    end_label: str
    source_status: str
    warnings: list[str] = Field(default_factory=list)


class EventContractValidationReport(BaseModel):
    """Validation report used by the V3.1 check script and debug endpoints."""

    valid: bool
    year: int
    duration_hours: int
    expected_duration_hours: int = 18
    time_window_count: int
    expected_time_window_count: int = 18
    starts_at: str
    ends_at: str
    contains_friday_saturday_split: bool
    crosses_midnight: bool
    issues: list[str] = Field(default_factory=list)
