"""Print V2.5 multi-genre classification reports for local validation.

Run from `backend/` with the virtual environment active:

    python scripts/classify_genres.py --year 2026
    python scripts/classify_genres.py --rebuild
"""

from pathlib import Path
import argparse
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.multi_genre_service import MultiGenreClassifierService  # noqa: E402


def main() -> None:
    """Print classified distribution for one edition or all artists."""
    parser = argparse.ArgumentParser(description="Classify Nexus artists with the V2.5 multi-genre layer.")
    parser.add_argument("--year", type=int, default=None, help="Optional Nexus edition year, for example 2026.")
    parser.add_argument("--rebuild", action="store_true", help="Persist artist_genres/evidence before printing.")
    parser.add_argument("--show-review", action="store_true", help="Print artists that still need manual review.")
    args = parser.parse_args()

    with SessionLocal() as db:
        service = MultiGenreClassifierService(db)
        if args.rebuild:
            result = service.rebuild(reset=True)
            print(f"Rebuilt V2.5 genre layer: {result.model_dump()}")

        if args.year:
            distribution = service.get_edition_genre_distribution(args.year)
            if distribution is None:
                raise SystemExit(f"Edition {args.year} was not found.")
            print(f"V2.5 genre distribution for {args.year}:")
            for item in distribution.distribution:
                print(f"- {item.name}: {item.artist_count}")
            print(f"Unknown artists: {distribution.unknown_artists}")
        else:
            print("V2.5 genre distribution across all artists:")
            for item in service.list_genres():
                print(f"- {item.name}: {item.artist_count}")

        if args.show_review:
            review = service.list_classified_artists(needs_review=True, limit=500).items
            print("\nArtists needing manual genre review:")
            for item in review:
                print(f"- {item.slug}: {item.main_genre} ({item.genre_confidence})")


if __name__ == "__main__":
    main()
