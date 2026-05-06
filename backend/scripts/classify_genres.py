"""Print a quick classified genre report for local validation.

Run from `backend/` with the virtual environment active:

    python scripts/classify_genres.py --year 2026
"""

from pathlib import Path
import argparse
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal
from app.services.genre_classifier import GenreClassifierService


def main() -> None:
    """Print classified distribution for one edition or all artists."""
    parser = argparse.ArgumentParser(description="Classify Nexus artists by hard dance subgenre.")
    parser.add_argument("--year", type=int, default=None, help="Optional Nexus edition year, for example 2026.")
    args = parser.parse_args()

    with SessionLocal() as db:
        service = GenreClassifierService(db)
        if args.year:
            distribution = service.get_edition_genre_distribution(args.year)
            if distribution is None:
                raise SystemExit(f"Edition {args.year} was not found.")
            print(f"Classified genre distribution for {args.year}:")
            for item in distribution.distribution:
                print(f"- {item.name}: {item.artist_count}")
            print(f"Unknown artists: {distribution.unknown_artists}")
            return

        print("Classified genre distribution across all artists:")
        for item in service.list_genres():
            print(f"- {item.name}: {item.artist_count}")


if __name__ == "__main__":
    main()
