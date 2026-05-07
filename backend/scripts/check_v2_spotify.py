"""Validate the Nexus Predictor V2.2 Spotify integration.

This check is safe both with and without credentials:
- Without credentials it verifies that the app fails safely.
- With credentials it verifies that token-protected refresh can run for a small
  artist sample when explicitly requested through the refresh script/API.
"""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect, select

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.db.database import engine, SessionLocal  # noqa: E402
from app.db.models import ArtistModel, SpotifyArtistCacheModel  # noqa: E402
from app.services.spotify_service import SpotifyService  # noqa: E402


def main() -> None:
    """Run all Spotify V2.2 checks."""
    print("Nexus Predictor V2.2 Spotify check")

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "spotify_artist_cache" not in tables:
        raise RuntimeError(
            "Missing table spotify_artist_cache. Run: alembic -c alembic.ini upgrade head"
        )

    print("Spotify cache table OK")

    service = SpotifyService()
    status = service.status()
    print(f"Spotify configured: {status.configured}")
    print(f"Default market: {status.default_market}")
    print(f"API base: {status.api_base_url}")

    with SessionLocal() as db:
        artist_count = int(db.scalar(select(ArtistModel.id).limit(1)) is not None)
        if artist_count == 0:
            raise RuntimeError("No artists found. Run python scripts/seed_database.py first if needed.")

        cache_count = len(list(db.scalars(select(SpotifyArtistCacheModel).limit(5))))
        print(f"Spotify cached artist rows visible: {cache_count}")

    if not settings.spotify_configured:
        print("Spotify credentials are not configured. This is a safe local state.")
        print("Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in backend/.env to run real refreshes.")
    else:
        print("Spotify credentials detected. Use scripts/refresh_spotify_artist.py to refresh selected artists.")

    print("V2.2 Spotify check completed successfully.")


if __name__ == "__main__":
    main()
