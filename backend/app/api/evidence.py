"""V2 evidence-layer endpoints.

These routes expose the data-quality foundation created in V2.1. They are
read-oriented by default, with one controlled manual-evidence endpoint so direct
knowledge from the project owner can be stored with confidence and notes.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.evidence import (
    ArtistEvidenceOverview,
    ArtistMetricRecord,
    CreateManualEvidenceRequest,
    EvidenceCoverage,
    EvidenceItemRecord,
    SourceRecord,
    VenuePrestigeRecord,
)
from app.services.evidence_seed_service import import_v1_evidence_layer
from app.services.evidence_service import EvidenceService

router = APIRouter()


@router.get("/coverage", response_model=ApiResponse[EvidenceCoverage])
def get_evidence_coverage(db: Session = Depends(get_db)) -> ApiResponse[EvidenceCoverage]:
    """Return high-level coverage counts for the V2 evidence layer."""
    service = EvidenceService(db)
    return ApiResponse(
        success=True,
        message="V2 evidence coverage loaded.",
        data=EvidenceCoverage(**service.get_coverage()),
    )


@router.post("/import-v1", response_model=ApiResponse[dict[str, int]])
def import_v1_evidence(
    reset: bool = Query(default=False, description="Delete and rebuild only V2 evidence-layer tables."),
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, int]]:
    """Import V1 JSON/seed data into V2 evidence tables.

    This endpoint is safe for local development. With reset=false it is
    idempotent and returns current counts when evidence already exists.
    """
    result = import_v1_evidence_layer(db, reset=reset)
    return ApiResponse(
        success=True,
        message="V1 dataset imported into V2 evidence layer.",
        data=result,
    )


@router.get("/sources", response_model=ApiResponse[list[SourceRecord]])
def list_sources(db: Session = Depends(get_db)) -> ApiResponse[list[SourceRecord]]:
    """List all source registry entries."""
    service = EvidenceService(db)
    return ApiResponse(
        success=True,
        message="Evidence sources loaded.",
        data=service.list_sources(),
    )


@router.get("/artists/{artist_slug}", response_model=ApiResponse[ArtistEvidenceOverview])
def get_artist_evidence(
    artist_slug: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> ApiResponse[ArtistEvidenceOverview]:
    """Return evidence, metrics and profile shells for one artist."""
    service = EvidenceService(db)
    overview = service.get_artist_overview(artist_slug, limit=limit)
    if overview is None:
        raise HTTPException(status_code=404, detail=f"Artist {artist_slug} was not found.")

    return ApiResponse(
        success=True,
        message=f"Evidence loaded for artist {artist_slug}.",
        data=ArtistEvidenceOverview(**overview),
    )


@router.get("/artists/{artist_slug}/metrics", response_model=ApiResponse[list[ArtistMetricRecord]])
def list_artist_metrics(
    artist_slug: str,
    db: Session = Depends(get_db),
) -> ApiResponse[list[ArtistMetricRecord]]:
    """Return derived V2 feature metrics for one artist."""
    service = EvidenceService(db)
    metrics = service.list_artist_metrics(artist_slug)
    if metrics is None:
        raise HTTPException(status_code=404, detail=f"Artist {artist_slug} was not found.")

    return ApiResponse(
        success=True,
        message=f"Evidence-backed metrics loaded for artist {artist_slug}.",
        data=metrics,
    )


@router.get("/venue-prestige", response_model=ApiResponse[list[VenuePrestigeRecord]])
def list_venue_prestige(db: Session = Depends(get_db)) -> ApiResponse[list[VenuePrestigeRecord]]:
    """Return initial venue/festival prestige seed rows."""
    service = EvidenceService(db)
    return ApiResponse(
        success=True,
        message="Venue and festival prestige seed loaded.",
        data=service.list_venue_prestige(),
    )


@router.post(
    "/manual",
    response_model=ApiResponse[EvidenceItemRecord],
    status_code=status.HTTP_201_CREATED,
)
def create_manual_evidence(
    payload: CreateManualEvidenceRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[EvidenceItemRecord]:
    """Create a manual evidence row for direct user knowledge or reviewed facts."""
    service = EvidenceService(db)
    evidence = service.create_manual_evidence(payload)
    if evidence is None:
        raise HTTPException(status_code=404, detail=f"Artist {payload.artist_slug} was not found.")

    return ApiResponse(
        success=True,
        message=f"Manual evidence registered for artist {payload.artist_slug}.",
        data=evidence,
    )
