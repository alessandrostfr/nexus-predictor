"""Venue data endpoints.

Block 1 stores Fabrik room and capacity data as a researched JSON seed. The
values are intentionally editable because public sources provide conflicting
capacity numbers depending on event configuration.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter

router = APIRouter()

VENUE_FILE = Path(__file__).resolve().parents[1] / "data" / "venue" / "fabrik_rooms.json"


def _read_json(path: Path) -> dict[str, Any]:
    """Read a UTF-8 JSON file from disk."""
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


@router.get("/fabrik")
def get_fabrik_venue() -> dict[str, object]:
    """Return Fabrik room and capacity seed data."""
    return {
        "success": True,
        "message": "Fabrik venue data loaded.",
        "data": _read_json(VENUE_FILE),
    }
