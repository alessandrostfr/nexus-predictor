"""Validate the V2.3 external-ingestion layer.

Run from backend/:

    python scripts/check_v2_external_ingestion.py
"""

from __future__ import annotations

import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.pipelines.flows.external_ingestion_flow import external_ingestion_flow  # noqa: E402
from app.services.external_ingestion_service import ExternalIngestionService  # noqa: E402


def main() -> None:
    """Run a deterministic validation pass."""
    print("Nexus Predictor V2.3 external-ingestion check")

    result = external_ingestion_flow(reset=True, limit_artists=8, probe_sources=False)
    print(f"Flow result: {result}")

    with SessionLocal() as db:
        coverage = ExternalIngestionService(db).coverage()

    print(f"Coverage: {coverage}")

    if coverage["external_sources"] < 3:
        raise RuntimeError("Expected at least three V2.3 external sources.")
    if coverage["external_career_events"] < 5:
        raise RuntimeError("Expected at least five external career events.")
    if coverage["artists_with_external_events"] < 5:
        raise RuntimeError("Expected at least five artists with external events.")
    if coverage["venue_prestige_items"] < 7:
        raise RuntimeError("Expected the venue/festival prestige catalog to be available.")

    print("V2.3 external-ingestion check completed successfully.")


if __name__ == "__main__":
    main()
