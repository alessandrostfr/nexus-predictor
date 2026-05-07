"""Validation script for V2.9 optimized timetable variants."""

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

from app.db.database import SessionLocal
from app.services.optimized_timetable_service import OptimizedTimetableService, VARIANT_ORDER


def main() -> None:
    """Run deterministic V2.9 validations."""
    with SessionLocal() as db:
        service = OptimizedTimetableService(db)
        print("Nexus Predictor V2.9 optimized timetable check")
        result = service.rebuild(2026, reset=True)
        print(f"Rebuild result: {result.model_dump()}")
        coverage = service.coverage(2026)
        print(f"Coverage: {coverage.model_dump() if coverage else None}")
        comparison = service.compare(2026)
        print(f"Comparison: {comparison.model_dump() if comparison else None}")
        integrity = service.integrity_report(2026)
        print(f"Integrity: {integrity.model_dump()}")

        if result.variants != 3:
            raise RuntimeError("Expected exactly 3 optimized variants.")
        if set(result.variant_keys) != set(VARIANT_ORDER):
            raise RuntimeError(f"Unexpected variant keys: {result.variant_keys}")
        if coverage is None or coverage.generated_variants != 3:
            raise RuntimeError("Coverage does not report all three variants.")
        if comparison is None or len(comparison.variants) != 3:
            raise RuntimeError("Comparison endpoint data is incomplete.")
        if not integrity.valid:
            raise RuntimeError(f"Optimized timetable integrity failed: {integrity.model_dump()}")

        for variant in comparison.variants:
            if variant.slot_count < 20:
                raise RuntimeError(f"Variant {variant.variant_key} has too few slots.")
            if variant.average_optimization_score <= 0:
                raise RuntimeError(f"Variant {variant.variant_key} has invalid optimization score.")

    print("V2.9 optimized timetable check completed successfully.")


if __name__ == "__main__":
    main()
