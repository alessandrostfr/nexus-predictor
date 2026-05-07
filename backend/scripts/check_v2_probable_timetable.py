"""Validation script for V2.8 probable timetable generation."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal
from app.services.probable_timetable_service import ProbableTimetableService


def main() -> None:
    """Rebuild and validate the V2.8 probable timetable."""
    with SessionLocal() as db:
        service = ProbableTimetableService(db)
        result = service.rebuild(2026, reset=True)
        coverage = service.coverage(2026)
        integrity = service.integrity_report(2026)
        overview = service.year_overview(2026)

        print("Nexus Predictor V2.8 probable timetable check")
        print(f"Rebuild result: {result.model_dump(mode='json')}")
        print(f"Coverage: {coverage.model_dump(mode='json') if coverage else None}")
        print(f"Integrity: {integrity.model_dump(mode='json')}")

        if result.slots < 20:
            raise RuntimeError("V2.8 generated too few timetable slots.")
        if result.official_available:
            raise RuntimeError("V2.8 probable timetable must not claim official availability.")
        if coverage is None or coverage.official_available:
            raise RuntimeError("Coverage must explicitly report official_available=false.")
        if coverage.assigned_artists != result.assigned_artists:
            raise RuntimeError("Coverage assigned artist count does not match rebuild result.")
        if coverage.total_rooms > 7:
            raise RuntimeError("V2.8 must stay within the seven-room Fabrik model.")
        if not integrity.valid:
            raise RuntimeError(f"V2.8 integrity check failed: {integrity.model_dump(mode='json')}")
        if not integrity.is_seven_room_fabrik_model:
            raise RuntimeError("V2.8 must use the verified seven-room Fabrik model.")
        if overview is None or overview.official_available:
            raise RuntimeError("Overview must explicitly state that the timetable is not official.")
        if not any("not an official" in note.lower() for note in overview.notes):
            raise RuntimeError("Overview must explain that V2.8 is not an official timetable.")

        print("V2.8 probable timetable check completed successfully.")


if __name__ == "__main__":
    main()
