"""CLI helper to generate V2.9 optimized timetable variants."""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Import path bootstrap
# ---------------------------------------------------------------------------
# When this script is executed as "python scripts/<script>.py", Python adds
# backend/scripts to sys.path instead of backend. Add backend explicitly so
# imports like "from app.db.database import SessionLocal" work on Windows,
# macOS and Linux without requiring PYTHONPATH.
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import argparse

from app.db.database import SessionLocal
from app.services.optimized_timetable_service import OptimizedTimetableService


def parse_args() -> argparse.Namespace:
    """Parse command-line flags."""
    parser = argparse.ArgumentParser(description="Generate V2.9 optimized timetable variants.")
    parser.add_argument("--year", type=int, default=2026, help="Edition year to optimize.")
    parser.add_argument("--reset", action="store_true", help="Delete existing optimized rows before generating.")
    return parser.parse_args()


def main() -> None:
    """Generate optimized variants and print the result."""
    args = parse_args()
    with SessionLocal() as db:
        service = OptimizedTimetableService(db)
        result = service.rebuild(args.year, reset=args.reset)
        print(result.model_dump())


if __name__ == "__main__":
    main()
