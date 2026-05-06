"""Generate a local prediction snapshot for a Nexus edition.

Usage:
    python scripts/generate_predictions.py --year 2026
"""

from argparse import ArgumentParser
from pathlib import Path
import sys

# Allow running the script directly from backend/ without installing the package.
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.prediction_service import PredictionService  # noqa: E402


def parse_args() -> ArgumentParser:
    """Build the CLI parser."""
    parser = ArgumentParser(description="Generate Nexus prediction snapshot JSON.")
    parser.add_argument("--year", type=int, default=2026, help="Edition year to generate.")
    return parser


def main() -> None:
    """Generate and print snapshot metadata."""
    args = parse_args().parse_args()
    with SessionLocal() as db:
        service = PredictionService(db)
        result = service.write_prediction_snapshot(args.year)

    if result is None:
        raise SystemExit(f"Edition {args.year} was not found.")

    print(f"Prediction snapshot generated for {result['year']}.")
    print(f"Artists scored: {result['artists']}")
    print(f"Output: {result['path']}")


if __name__ == "__main__":
    main()
