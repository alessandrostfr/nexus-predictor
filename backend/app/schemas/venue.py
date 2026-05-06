"""Pydantic schemas for Fabrik venue API responses."""

from typing import Any

from pydantic import BaseModel


class RoomSummary(BaseModel):
    """One Fabrik room or area with editable capacity range."""

    name: str
    aliases: list[str] = []
    min_capacity: int | None = None
    estimated_capacity: int | None = None
    max_capacity: int | None = None
    confidence: str = "pending"
    source_keys: list[str] = []
    notes: str | None = None


class VenueDetail(BaseModel):
    """Venue-level payload including capacity summary and rooms."""

    venue: str
    status: str
    address: str | None = None
    capacity_summary: dict[str, Any]
    rooms: list[RoomSummary]
    sources: list[dict[str, Any]]
