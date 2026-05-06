"""Validate the researched JSON dataset and SQLite seed.

Run from `backend/` with the virtual environment active:

    python scripts/validate_dataset.py
"""


from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal
from app.repositories.json_repository import JsonSeedRepository
from app.services.database_seed_service import get_database_status, seed_database_from_json

repository = JsonSeedRepository()


def validate_json_seed() -> None:
    """Validate the minimum JSON dataset needed by the API."""
    editions = repository.list_editions()
    artist_index = repository.get_artist_index()
    venue = repository.get_venue()

    assert len(editions) == 5, "Expected exactly five Nexus edition files."
    assert {edition["year"] for edition in editions} == {2022, 2023, 2024, 2025, 2026}

    edition_2026 = repository.get_edition(2026)
    assert edition_2026 is not None, "The 2026 edition file is missing."
    assert len(edition_2026.get("lineup", [])) >= 60, "The 2026 lineup looks incomplete."

    artists = artist_index.get("artists", [])
    assert len(artists) >= 100, "The artist index should contain historical artists."
    assert any(artist["slug"] == "project-one" for artist in artists), "Project One is missing."

    rooms = venue.get("rooms", [])
    assert len(rooms) >= 6, "Fabrik room seed should include several areas."
    assert any(room["name"] == "Main Room" for room in rooms), "Main Room is missing."


def validate_sqlite_seed() -> None:
    """Reset SQLite from JSON and verify row counts."""
    with SessionLocal() as db:
        seed_database_from_json(db, reset=True)
        status = get_database_status(db)

    assert status["seeded"] is True, "SQLite database was not seeded."
    assert status["editions"] == 5, "SQLite edition count is wrong."
    assert status["artists"] >= 100, "SQLite artist count is too low."
    assert status["rooms"] >= 6, "SQLite room count is too low."


def main() -> None:
    """Run all dataset validations."""
    validate_json_seed()
    validate_sqlite_seed()
    print("Dataset JSON and SQLite seed validation completed successfully.")


if __name__ == "__main__":
    main()
