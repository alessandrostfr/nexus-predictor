"""Refresh one Nexus artist from Spotify into V2 evidence tables.

Usage:

    python scripts/refresh_spotify_artist.py project-one --force

Requires SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in backend/.env.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.spotify_service import SpotifyService  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Refresh Spotify data for one Nexus artist.")
    parser.add_argument("artist_slug", help="Nexus artist slug, e.g. project-one or angerfist.")
    parser.add_argument("--force", action="store_true", help="Refresh even when cache already exists.")
    parser.add_argument("--market", default=None, help="Optional Spotify market override, e.g. ES, NL or US.")
    return parser.parse_args()


def main() -> None:
    """Run a single Spotify artist refresh."""
    args = parse_args()
    service = SpotifyService()

    with SessionLocal() as db:
        result = service.refresh_artist(db, args.artist_slug, force=args.force, market=args.market)

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
