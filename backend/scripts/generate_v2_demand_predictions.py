"""Generate V2.7 demand predictions from the command line.

Usage from backend/:
    python scripts/generate_v2_demand_predictions.py --year 2026 --reset
"""

from argparse import ArgumentParser
from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.demand_model_service import DemandModelService  # noqa: E402


def parse_args() -> ArgumentParser:
    """Build the CLI parser."""
    parser = ArgumentParser(description="Generate Nexus Predictor V2.7 demand predictions.")
    parser.add_argument("--year", type=int, default=2026, help="Edition year to score.")
    parser.add_argument("--reset", action="store_true", help="Delete and rebuild existing rows for the year.")
    return parser


def main() -> None:
    """Generate predictions and print a compact summary."""
    args = parse_args().parse_args()
    with SessionLocal() as db:
        result = DemandModelService(db).rebuild(args.year, reset=args.reset)
    print(result.model_dump(mode="json"))


if __name__ == "__main__":
    main()
