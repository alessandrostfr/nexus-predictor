"""Central filesystem paths for the backend.

The project still uses editable JSON files as the source of truth during the
research blocks. Keeping paths in one module prevents each endpoint or service
from rebuilding filesystem locations in a different way.
"""

from pathlib import Path

# backend/app/core/paths.py -> backend/app -> backend
APP_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = APP_DIR.parent
DATA_DIR = APP_DIR / "data"
EDITIONS_DIR = DATA_DIR / "editions"
ARTISTS_DIR = DATA_DIR / "artists"
VENUE_DIR = DATA_DIR / "venue"
SOURCES_DIR = DATA_DIR / "sources"
ARTIST_PROFILE_CACHE_PATH = ARTISTS_DIR / "enriched_artists.json"
GENRE_OVERRIDES_PATH = ARTISTS_DIR / "genre_overrides.json"
MANUAL_OVERRIDES_PATH = ARTISTS_DIR / "manual_overrides.json"

PREDICTIONS_DIR = DATA_DIR / "predictions"
