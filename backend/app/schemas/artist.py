"""Pydantic schemas for artist seed API responses."""

from typing import Any

from pydantic import BaseModel


class ArtistSummary(BaseModel):
    """Compact artist payload for lists and search results."""

    slug: str
    name: str
    normalized_name: str
    primary_genre_seed: str = "Unknown"
    appearance_count: int = 0
    appearance_years: list[int] = []
    manual_review: bool = False
    data_status: str = "seed_from_lineup"


class ArtistDetail(ArtistSummary):
    """Detailed artist payload with appearances and raw seed data."""

    appearances: list[dict[str, Any]] = []
    raw: dict[str, Any]
