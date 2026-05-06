"""Read-only repository for editable JSON seed files."""

import json
from pathlib import Path
from typing import Any

from app.core.paths import ARTISTS_DIR, EDITIONS_DIR, VENUE_DIR


class JsonSeedRepository:
    """Load researched seed data from JSON files.

    JSON files remain useful because they are easy to review and correct during
    research. Block 2 copies those files into SQLite for API usage, but the JSON
    repository remains the importer source.
    """

    def read_json(self, path: Path) -> dict[str, Any]:
        """Read one UTF-8 encoded JSON file."""
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def list_editions(self) -> list[dict[str, Any]]:
        """Return all researched edition seed files sorted by year."""
        return [self.read_json(path) for path in sorted(EDITIONS_DIR.glob("*.json"))]

    def get_edition(self, year: int) -> dict[str, Any] | None:
        """Return one edition seed by year or `None` when it does not exist."""
        path = EDITIONS_DIR / f"{year}.json"
        return self.read_json(path) if path.exists() else None

    def get_artist_index(self) -> dict[str, Any]:
        """Return the normalized artist index generated in Block 1."""
        return self.read_json(ARTISTS_DIR / "artist_index.json")

    def get_venue(self) -> dict[str, Any]:
        """Return the researched Fabrik room capacity seed."""
        return self.read_json(VENUE_DIR / "fabrik_rooms.json")
