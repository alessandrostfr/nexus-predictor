"""Pydantic schemas for festival edition API responses."""

from typing import Any

from pydantic import BaseModel


class EditionSummary(BaseModel):
    """Small edition object used in list endpoints."""

    year: int
    name: str
    status: str
    venue: str
    date_start: str | None = None
    date_end: str | None = None
    artist_count: int
    stage_count: int


class EditionDetail(EditionSummary):
    """Detailed edition payload with raw researched fields."""

    city: str | None = None
    duration_hours: int | None = None
    attendance: dict[str, Any]
    lineup: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    raw: dict[str, Any]


class EditionLineupItem(BaseModel):
    """One performance from an edition lineup."""

    display_name: str
    artists: list[str]
    performance_type: str
    stage: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    source_key: str | None = None
    manual_review: bool = False
