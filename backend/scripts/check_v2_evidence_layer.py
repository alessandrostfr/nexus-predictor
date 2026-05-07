"""Validate the V2.1 evidence-layer setup.

Run from `backend/` after Alembic migrations:

    python scripts/check_v2_evidence_layer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.evidence_seed_service import import_v1_evidence_layer  # noqa: E402
from app.services.evidence_service import EvidenceService  # noqa: E402


def assert_minimum(name: str, value: int, minimum: int) -> None:
    """Raise a clear error when a count is lower than expected."""
    if value < minimum:
        raise RuntimeError(f"{name} expected >= {minimum}, got {value}")


def main() -> None:
    """Run V2.1 evidence-layer validation checks."""
    print("Nexus Predictor V2.1 evidence-layer check")
    with SessionLocal() as db:
        seed_result = import_v1_evidence_layer(db, reset=False)
        coverage = EvidenceService(db).get_coverage()

    print("Seed result:", seed_result)
    print("Coverage:", coverage)

    assert_minimum("artists", coverage["artists"], 100)
    assert_minimum("sources", coverage["sources"], 5)
    assert_minimum("evidence_items", coverage["evidence_items"], 300)
    assert_minimum("artist_metrics", coverage["artist_metrics"], 200)
    assert_minimum("artists_with_evidence", coverage["artists_with_evidence"], 100)
    assert_minimum("venue_prestige_items", coverage["venue_prestige_items"], 1)

    print("V2.1 evidence-layer check completed successfully.")


if __name__ == "__main__":
    main()
