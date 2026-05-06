"""Schemas for genre seed endpoints.

Block 2 only exposes genre seeds already present in the dataset. The real hard
dance taxonomy and override classifier belongs to Block 4.
"""

from pydantic import BaseModel


class GenreSeed(BaseModel):
    """A genre label currently present in the artist seed data."""

    name: str
    artist_count: int


class EditionGenreDistribution(BaseModel):
    """Genre distribution for one edition based on current seed values."""

    year: int
    distribution: list[GenreSeed]
