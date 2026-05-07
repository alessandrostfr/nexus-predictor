"""Validate Nexus Predictor V2.6 historical timetable dataset.

Run from backend/ with the virtual environment active:

    python scripts/check_v2_historical_timetables.py
"""

from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.historical_timetable_service import HistoricalTimetableService  # noqa: E402


def main() -> None:
    """Run concrete V2.6 validation checks against the local database."""
    with SessionLocal() as db:
        service = HistoricalTimetableService(db)
        result = service.import_seed(reset=True)
        coverage = result.coverage
        integrity = service.integrity_report()

        print("Nexus Predictor V2.6 historical timetable check")
        print(f"Import result: {result.model_dump()}")
        print(f"Integrity: {integrity.model_dump()}")

        assert result.slots >= 200, "Expected a meaningful historical timetable slot dataset."
        assert coverage.years == [2022, 2023, 2024, 2025], "Expected historical years 2022-2025."
        assert coverage.total_days == 6, "Expected 2022, 2023 and Friday/Saturday for 2024 and 2025."
        assert coverage.slots_with_artist_slug == coverage.total_slots, "Every slot should resolve an artist slug."
        assert coverage.slots_with_source == coverage.total_slots, "Every slot should keep source metadata."
        assert coverage.year_2025_is_seven_room_model, "2025 must be normalized to the verified seven-room model."
        assert set(coverage.year_2025_rooms) == {
            "Area 19",
            "Club Area",
            "Crystal Area",
            "Hangar",
            "Main Room",
            "Open Air",
            "Satelite",
        }
        assert integrity.valid, "Historical timetable integrity checks should pass."
        assert integrity.overlap_count == 0, "No overlaps should exist inside the same room/day."

        overview_2025 = service.year_overview(2025)
        assert overview_2025 is not None, "2025 overview should exist."
        assert overview_2025.room_count == 7, "2025 overview should expose exactly seven rooms."
        assert len(overview_2025.days) == 2, "2025 should expose Friday and Saturday."

        main_room_2025 = service.list_slots(year=2025, room="Main Room", limit=200)
        assert main_room_2025.total > 0, "Main Room should have historical 2025 slots."
        assert all(slot.room_name == "Main Room" for slot in main_room_2025.items)

        alias_room_2025 = service.list_slots(year=2025, room="New Crystal", limit=200)
        assert alias_room_2025.total > 0, "New Crystal alias should resolve to Crystal Area."
        assert all(slot.room_name == "Crystal Area" for slot in alias_room_2025.items)

        headliners = service.list_slots(year=2025, only_headliners=True, limit=200)
        assert headliners.total > 0, "Historical headliner slots should be marked."

        print("V2.6 historical timetable check completed successfully.")


if __name__ == "__main__":
    main()
