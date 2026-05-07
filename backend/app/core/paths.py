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
TIMETABLES_DIR = DATA_DIR / "timetables"
HISTORICAL_TIMETABLES_PATH = TIMETABLES_DIR / "historical_2022_2025.json"
PREDICTIONS_DIR = DATA_DIR / "predictions"
EXTERNAL_INGESTION_DIR = DATA_DIR / "external_ingestion"
SOCIAL_PLATFORMS_DIR = DATA_DIR / "social_platforms"

ARTIST_PROFILE_CACHE_PATH = ARTISTS_DIR / "enriched_artists.json"
GENRE_OVERRIDES_PATH = ARTISTS_DIR / "genre_overrides.json"
MANUAL_OVERRIDES_PATH = ARTISTS_DIR / "manual_overrides.json"
EXTERNAL_RESEARCH_SEED_PATH = EXTERNAL_INGESTION_DIR / "external_research_seed.json"
SOCIAL_PLATFORM_SEED_PATH = SOCIAL_PLATFORMS_DIR / "social_platform_seed.json"
MANUAL_SOCIAL_METRICS_CSV_PATH = SOCIAL_PLATFORMS_DIR / "manual_social_metrics.csv"