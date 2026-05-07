"""Import V1 JSON seed data into the V2 evidence layer.

Run from `backend/` with the virtual environment active:

    python scripts/seed_v2_evidence.py

Use --reset to rebuild only V2 evidence tables while preserving V1 editions,
artists and rooms:

    python scripts/seed_v2_evidence.py --reset
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.evidence_seed_service import import_v1_evidence_layer  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Seed Nexus Predictor V2 evidence layer.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and rebuild only V2 evidence-layer tables.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the V2 evidence import."""
    args = parse_args()
    with SessionLocal() as db:
        result = import_v1_evidence_layer(db, reset=args.reset)

    print("V2 evidence seed result:", result)


if __name__ == "__main__":
    main()
