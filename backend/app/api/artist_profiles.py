"""Enriched artist profile endpoints.

These endpoints sit beside the raw lineup artist endpoints. They return profiles
prepared for the future frontend artist pages: image, bio, links, aliases, top
tracks and latest releases when those fields are available in the local cache or
external APIs.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.artist_enrichment import ArtistProfile, ArtistProfileList, ArtistRefreshResult
from app.schemas.common import ApiResponse
from app.services.artist_enrichment_service import ArtistEnrichmentService

router = APIRouter()


@router.get("", response_model=ApiResponse[ArtistProfileList])
def list_artist_profiles(
    year: int | None = Query(default=None, description="Filter profiles by Nexus edition year."),
    q: str | None = Query(default=None, description="Search by artist name."),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[ArtistProfileList]:
    """Return enriched artist profiles with optional filters."""
    service = ArtistEnrichmentService(db)
    return ApiResponse(
        success=True,
        message="Artist profiles loaded.",
        data=service.list_profiles(year=year, query=q, limit=limit, offset=offset),
    )


@router.get("/{slug}", response_model=ApiResponse[ArtistProfile])
def get_artist_profile(slug: str, db: Session = Depends(get_db)) -> ApiResponse[ArtistProfile]:
    """Return one enriched artist profile by slug."""
    service = ArtistEnrichmentService(db)
    profile = service.get_profile(slug)

    if profile is None:
        raise HTTPException(status_code=404, detail=f"Artist profile {slug} was not found.")

    return ApiResponse(success=True, message=f"Artist profile {slug} loaded.", data=profile)


@router.post("/{slug}/refresh", response_model=ApiResponse[ArtistRefreshResult])
def refresh_artist_profile(
    slug: str,
    use_external_apis: bool = Query(
        default=False,
        description="Call external APIs only when this and ENABLE_EXTERNAL_ARTIST_ENRICHMENT are true.",
    ),
    force: bool = Query(default=False, description="Refresh even when cached enrichment already exists."),
    db: Session = Depends(get_db),
) -> ApiResponse[ArtistRefreshResult]:
    """Refresh one profile into the local JSON cache.

    By default this endpoint only materializes the internal seed profile into the
    cache. Real external calls require an explicit query flag and environment
    setting so local validation remains deterministic.
    """
    service = ArtistEnrichmentService(db)
    result = service.refresh_profile(slug, use_external_apis=use_external_apis, force=force)

    if result is None:
        raise HTTPException(status_code=404, detail=f"Artist profile {slug} was not found.")

    return ApiResponse(success=True, message=f"Artist profile {slug} refresh completed.", data=result)
