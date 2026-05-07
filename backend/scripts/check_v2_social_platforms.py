"""Validate Nexus Predictor V2.4 social/platform ingestion locally."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.database import SessionLocal  # noqa: E402
from app.services.social_platform_service import SocialPlatformService  # noqa: E402


def main() -> None:
    """Run a deterministic V2.4 sanity check."""
    print("Nexus Predictor V2.4 social/platform check")
    db = SessionLocal()
    try:
        service = SocialPlatformService(db)
        summary = service.run(reset=False)
        coverage = service.coverage()
        angerfist = service.artist_overview("angerfist")

        print(f"Run summary: {summary}")
        print(f"Coverage: {coverage}")

        if coverage["social_profiles"] <= 0:
            raise RuntimeError("No social profiles were imported.")
        if coverage["platform_profiles"] <= 0:
            raise RuntimeError("No music-platform profiles were imported.")
        if coverage["social_artist_metrics"] <= 0:
            raise RuntimeError("No V2.4 artist metrics were generated.")
        if coverage["artists_with_scores"] <= 0:
            raise RuntimeError("No social score metrics were generated.")
        if angerfist is None or not angerfist["metrics"]:
            raise RuntimeError("Expected V2.4 metrics for angerfist.")
    finally:
        db.close()

    print("V2.4 social/platform check completed successfully.")


if __name__ == "__main__":
    main()
