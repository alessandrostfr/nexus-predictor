"""Prefect tasks for V2.4 social and music-platform ingestion."""

from __future__ import annotations

from prefect import task

from app.core.paths import MANUAL_SOCIAL_METRICS_CSV_PATH, SOCIAL_PLATFORM_SEED_PATH
from app.db.database import SessionLocal
from app.services.social_platform_service import SocialPlatformService


@task(name="load-social-platform-inputs")
def load_social_platform_inputs() -> dict[str, object]:
    """Report input-file availability before running the service."""
    return {
        "json_seed_exists": SOCIAL_PLATFORM_SEED_PATH.exists(),
        "json_seed_path": str(SOCIAL_PLATFORM_SEED_PATH),
        "manual_csv_exists": MANUAL_SOCIAL_METRICS_CSV_PATH.exists(),
        "manual_csv_path": str(MANUAL_SOCIAL_METRICS_CSV_PATH),
    }


@task(name="run-social-platform-service")
def run_social_platform_service(reset: bool = False, limit_artists: int | None = None) -> dict[str, object]:
    """Run the V2.4 ingestion service inside a managed DB session."""
    db = SessionLocal()
    try:
        service = SocialPlatformService(db)
        return service.run(reset=reset, limit_artists=limit_artists)
    finally:
        db.close()


@task(name="social-platform-coverage")
def social_platform_coverage() -> dict[str, object]:
    """Return coverage after ingestion."""
    db = SessionLocal()
    try:
        service = SocialPlatformService(db)
        return service.coverage()
    finally:
        db.close()
