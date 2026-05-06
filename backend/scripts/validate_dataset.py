"""Validate Block 1 JSON dataset files.

Run from the backend folder with the virtual environment active:

    python scripts/validate_dataset.py
"""

import json
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "app" / "data"


def read_json(path: Path) -> dict:
    """Read a JSON file and return its parsed content."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def main() -> None:
    """Validate the minimum dataset contract used by the API and tests."""
    edition_files = sorted((DATA_DIR / "editions").glob("*.json"))

    if len(edition_files) != 5:
        raise RuntimeError(f"Expected 5 edition files, found {len(edition_files)}.")

    for edition_file in edition_files:
        edition = read_json(edition_file)
        year = edition.get("year")
        lineup = edition.get("lineup", [])

        if not year:
            raise RuntimeError(f"{edition_file} does not include a year.")

        if not lineup:
            raise RuntimeError(f"{edition_file} does not include lineup data.")

        print(f"OK {year}: {len(lineup)} performances")

    venue = read_json(DATA_DIR / "venue" / "fabrik_rooms.json")
    print(f"OK venue rooms: {len(venue.get('rooms', []))}")

    artist_index = read_json(DATA_DIR / "artists" / "artist_index.json")
    print(f"OK artists: {artist_index.get('total_artists')}")

    print("Dataset validation completed.")


if __name__ == "__main__":
    main()
