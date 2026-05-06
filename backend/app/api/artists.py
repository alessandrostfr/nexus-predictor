"""Artist seed endpoints.

The real artist enrichment block will add Spotify, Last.fm, MusicBrainz and bio
data. For now this endpoint exposes the normalized lineup-based artist index.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()

ARTIST_INDEX_FILE = Path(__file__).resolve().parents[1] / "data" / "artists" / "artist_index.json"


def _read_artist_index() -> dict[str, Any]:
    """Read the generated artist index from disk."""
    with ARTIST_INDEX_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


@router.get("")
def list_artists() -> dict[str, object]:
    """Return all artists extracted from the researched lineup seeds."""
    return {
        "success": True,
        "message": "Artist index loaded.",
        "data": _read_artist_index(),
    }


@router.get("/{slug}")
def get_artist(slug: str) -> dict[str, object]:
    """Return one artist by slug."""
    artist_index = _read_artist_index()

    for artist in artist_index.get("artists", []):
        if artist.get("slug") == slug:
            return {
                "success": True,
                "message": f"Artist {slug} loaded.",
                "data": artist,
            }

    raise HTTPException(status_code=404, detail=f"Artist {slug} was not found.")
