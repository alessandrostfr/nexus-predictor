"""Festival edition endpoints.

For Block 0 these endpoints read small JSON placeholders. In Block 1 we will
replace the placeholders with researched Nexus Festival historical data.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()

# `parents[1]` points to `backend/app`, then we enter the data folder.
EDITIONS_DIR = Path(__file__).resolve().parents[1] / "data" / "editions"


def _read_edition_file(path: Path) -> dict[str, Any]:
    """Read one edition JSON file using UTF-8 encoding."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@router.get("")
def list_editions() -> dict[str, object]:
    """List all available festival edition files."""
    editions = []

    for path in sorted(EDITIONS_DIR.glob("*.json")):
        edition = _read_edition_file(path)
        editions.append(
            {
                "year": edition.get("year"),
                "name": edition.get("name"),
                "status": edition.get("status"),
            }
        )

    return {
        "success": True,
        "message": "Festival editions loaded.",
        "data": editions,
    }


@router.get("/{year}")
def get_edition(year: int) -> dict[str, object]:
    """Return one festival edition by year."""
    path = EDITIONS_DIR / f"{year}.json"

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")

    return {
        "success": True,
        "message": f"Edition {year} loaded.",
        "data": _read_edition_file(path),
    }
