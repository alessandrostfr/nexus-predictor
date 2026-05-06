"""Materialize or refresh artist profiles.

Examples:
    python scripts/enrich_artists.py --slug angerfist
    python scripts/enrich_artists.py --slug angerfist --external --force
    python scripts/enrich_artists.py --year 2026 --limit 20
"""

import argparse
from pathlib import Path
import sys

# Make `app` importable when running from the backend folder.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.artist_enrichment_service import ArtistEnrichmentService  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Refresh Nexus Predictor artist profiles.")
    parser.add_argument("--slug", help="Artist slug to refresh, for example angerfist.")
    parser.add_argument("--year", type=int, help="Refresh artists appearing in a specific edition year.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum artists to process when using --year.")
    parser.add_argument("--external", action="store_true", help="Allow external API calls when settings also enable them.")
    parser.add_argument("--force", action="store_true", help="Refresh even when the cache already has data.")
    return parser.parse_args()


def main() -> None:
    """Run the enrichment CLI."""
    args = parse_args()

    with SessionLocal() as db:
        service = ArtistEnrichmentService(db)
        if args.slug:
            result = service.refresh_profile(
                args.slug,
                use_external_apis=args.external,
                force=args.force,
            )
            if result is None:
                raise SystemExit(f"Artist '{args.slug}' was not found.")
            print(f"{result.slug}: refreshed={result.refreshed} external={result.external_calls_enabled}")
            for warning in result.warnings:
                print(f"  warning: {warning}")
            return

        profiles = service.list_profiles(year=args.year, limit=args.limit, offset=0).items
        for profile in profiles:
            result = service.refresh_profile(
                profile.slug,
                use_external_apis=args.external,
                force=args.force,
            )
            if result is None:
                continue
            print(f"{result.slug}: refreshed={result.refreshed} external={result.external_calls_enabled}")


if __name__ == "__main__":
    main()
