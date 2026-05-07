"""Run the V2.4 social and music-platform ingestion pipeline.

Examples:

    python scripts/run_social_platform_ingestion.py --reset
    python scripts/run_social_platform_ingestion.py --lastfm angerfist --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.pipelines.flows.social_platforms_flow import social_platform_ingestion_flow  # noqa: E402
from app.services.social_platform_service import SocialPlatformService  # noqa: E402


def refresh_lastfm_artist(artist_slug: str, *, force: bool) -> None:
    """Refresh one artist directly from Last.fm without starting the full flow."""
    db = SessionLocal()
    try:
        service = SocialPlatformService(db)
        result = service.refresh_lastfm_artist(artist_slug, force=force)
        print(result)
    finally:
        db.close()


def main() -> None:
    """Parse CLI arguments and run either the flow or Last.fm refresh."""
    parser = argparse.ArgumentParser(description="Run Nexus Predictor V2.4 social/platform ingestion.")
    parser.add_argument("--reset", action="store_true", help="Rebuild only V2.4 social/platform rows.")
    parser.add_argument("--limit-artists", type=int, default=None, help="Optional artist limit for quick tests.")
    parser.add_argument("--lastfm", type=str, default=None, help="Refresh Last.fm top tracks for one artist slug.")
    parser.add_argument("--force", action="store_true", help="Force Last.fm refresh if cached.")
    args = parser.parse_args()

    if args.lastfm:
        refresh_lastfm_artist(args.lastfm, force=args.force)
        return

    result = social_platform_ingestion_flow(reset=args.reset, limit_artists=args.limit_artists)
    print(result)


if __name__ == "__main__":
    main()
