"""V3.3 artist identity-resolution endpoints.

These routes are admin/debug oriented. They expose canonical artist identities,
aliases, links and candidate review without pretending any external profile is
safe for ML before confidence gates pass.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.identity import (
    ArtistIdentityCandidateListResponse,
    ArtistMasterDetail,
    ArtistMasterListResponse,
    IdentityConventionsResponse,
    IdentityCoverageResponse,
    IdentityRebuildResult,
    ReviewIdentityCandidateRequest,
    ReviewIdentityCandidateResult,
)
from app.services.identity_resolution_service import ArtistIdentityResolutionService

router = APIRouter()


@router.post("/rebuild", response_model=ApiResponse[IdentityRebuildResult])
def rebuild_identity_layer(
    reset: bool = Query(default=True, description="Delete and rebuild V3.3 identity tables from current seed/profile data."),
    db: Session = Depends(get_db),
) -> ApiResponse[IdentityRebuildResult]:
    """Rebuild the V3.3 identity-resolution layer."""
    service = ArtistIdentityResolutionService(db)
    return ApiResponse(success=True, message="V3.3 identity layer rebuilt.", data=service.rebuild(reset=reset))


@router.get("/coverage", response_model=ApiResponse[IdentityCoverageResponse])
def get_identity_coverage(db: Session = Depends(get_db)) -> ApiResponse[IdentityCoverageResponse]:
    """Return identity coverage and feature-eligibility guardrails."""
    service = ArtistIdentityResolutionService(db)
    coverage = service.coverage()
    return ApiResponse(success=coverage.ready, message="V3.3 identity coverage loaded.", data=coverage)


@router.get("/artists", response_model=ApiResponse[ArtistMasterListResponse])
def list_identity_artists(
    q: str | None = Query(default=None, description="Search by canonical key or display name."),
    needs_review: bool | None = Query(default=None, description="Filter canonical artists that need manual profile review."),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[ArtistMasterListResponse]:
    """List canonical artist identities."""
    service = ArtistIdentityResolutionService(db)
    return ApiResponse(
        success=True,
        message="V3.3 canonical artists loaded.",
        data=service.list_artists(query=q, needs_review=needs_review, limit=limit, offset=offset),
    )


@router.get("/artists/{canonical_artist_key}", response_model=ApiResponse[ArtistMasterDetail])
def get_identity_artist(canonical_artist_key: str, db: Session = Depends(get_db)) -> ApiResponse[ArtistMasterDetail]:
    """Return one canonical artist with aliases and links."""
    service = ArtistIdentityResolutionService(db)
    artist = service.get_artist(canonical_artist_key)
    if artist is None:
        raise HTTPException(status_code=404, detail=f"Canonical artist {canonical_artist_key} was not found.")
    return ApiResponse(success=True, message=f"V3.3 identity loaded for {canonical_artist_key}.", data=artist)


@router.get("/candidates", response_model=ApiResponse[ArtistIdentityCandidateListResponse])
def list_identity_candidates(
    status: str | None = Query(default=None, description="Filter by pending_review, verified or rejected."),
    confidence: str | None = Query(default=None, description="Optional confidence filter."),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[ArtistIdentityCandidateListResponse]:
    """List external-profile candidates for admin review."""
    service = ArtistIdentityResolutionService(db)
    return ApiResponse(
        success=True,
        message="V3.3 identity candidates loaded.",
        data=service.list_candidates(status=status, confidence=confidence, limit=limit, offset=offset),
    )


@router.post("/candidates/{candidate_id}/review", response_model=ApiResponse[ReviewIdentityCandidateResult])
def review_identity_candidate(
    candidate_id: int,
    payload: ReviewIdentityCandidateRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[ReviewIdentityCandidateResult]:
    """Verify or reject an external-profile candidate."""
    service = ArtistIdentityResolutionService(db)
    try:
        result = service.review_candidate(candidate_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail=f"Identity candidate {candidate_id} was not found.")
    return ApiResponse(success=True, message=result.message, data=result)


@router.get("/conventions", response_model=ApiResponse[IdentityConventionsResponse])
def get_identity_conventions(db: Session = Depends(get_db)) -> ApiResponse[IdentityConventionsResponse]:
    """Return identity-resolution confidence and feature-eligibility policies."""
    service = ArtistIdentityResolutionService(db)
    return ApiResponse(success=True, message="V3.3 identity conventions loaded.", data=service.conventions())
