"""Pydantic schemas for database maintenance endpoints."""

from pydantic import BaseModel


class DatabaseStatus(BaseModel):
    """Current local SQLite dataset status."""

    database_url: str
    editions: int
    artists: int
    rooms: int
    seeded: bool
    source: str
    last_seeded_at: str | None = None
