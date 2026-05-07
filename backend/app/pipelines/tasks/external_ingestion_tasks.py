"""Reusable Prefect tasks for V2.3 external ingestion."""

from __future__ import annotations

from typing import Any

import httpx
from prefect import task
from sqlalchemy.orm import Session

from app.services.external_ingestion_service import ExternalIngestionService


@task(name="load-external-ingestion-seed")
def load_external_ingestion_seed() -> dict[str, Any]:
    """Load the deterministic V2.3 seed through the service."""
    # The task intentionally does not require a DB session. It validates that
    # the local seed exists before the flow starts writing rows.
    service = ExternalIngestionService(db=None)  # type: ignore[arg-type]
    return service.load_seed()


@task(name="run-external-ingestion-service")
def run_external_ingestion_service(
    *,
    reset: bool,
    limit_artists: int | None,
) -> dict[str, Any]:
    """Run the persistence step inside a short-lived database session."""
    from app.db.database import SessionLocal

    with SessionLocal() as db:
        service = ExternalIngestionService(db)
        return service.run(reset=reset, limit_artists=limit_artists)


@task(name="external-ingestion-coverage")
def get_external_ingestion_coverage() -> dict[str, int]:
    """Return a V2.3 coverage snapshot."""
    from app.db.database import SessionLocal

    with SessionLocal() as db:
        service = ExternalIngestionService(db)
        return service.coverage()


@task(name="probe-source-url")
def probe_source_url(source_key: str, source_url: str | None, timeout_seconds: float = 8.0) -> dict[str, Any]:
    """Best-effort URL probe used only when explicitly enabled.

    Network checks are deliberately non-blocking: a failed source records a
    warning but never prevents the ingestion pipeline from persisting local data.
    """
    if not source_url:
        return {"source_key": source_key, "source_url": None, "ok": False, "status_code": None, "error": "missing_url"}

    try:
        response = httpx.get(
            source_url,
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": "NexusPredictorV2/0.3 external-ingestion-check"},
        )
        return {
            "source_key": source_key,
            "source_url": source_url,
            "ok": response.status_code < 500,
            "status_code": response.status_code,
            "error": None,
        }
    except httpx.HTTPError as exc:
        return {
            "source_key": source_key,
            "source_url": source_url,
            "ok": False,
            "status_code": None,
            "error": str(exc),
        }
