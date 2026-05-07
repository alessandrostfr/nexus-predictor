"""Generate the V2.8 probable 2026 timetable from the command line."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal
from app.services.probable_timetable_service import ProbableTimetableService


def main() -> None:
    """Run the V2.8 probable timetable generator."""
    parser = argparse.ArgumentParser(description="Generate V2.8 probable Nexus timetable.")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--reset", action="store_true", help="Delete and rebuild existing probable timetable rows.")
    args = parser.parse_args()

    with SessionLocal() as db:
        result = ProbableTimetableService(db).rebuild(args.year, reset=args.reset)
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
