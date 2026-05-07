"""V2.4 social and music-platform API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.social_platforms import (
    ArtistSocialOverview,
    LastfmRefreshResult,
    SocialPlatformCoverage,
    SocialPlatformRunSummary,
    SocialPlatformStatus,
)
from app.services.social_platform_service import SocialPlatformService

router = APIRouter()


@router.get("/status", response_model=ApiResponse[SocialPlatformStatus])
def get_social_platform_status(db: Session = Depends(get_db)) -> ApiResponse[SocialPlatformStatus]:
    """Return safe V2.4 integration status without exposing secrets."""
    service = SocialPlatformService(db)
    return ApiResponse(
        success=True,
        message="Social and music-platform integration status loaded.",
        data=SocialPlatformStatus(**service.status()),
    )


@router.post("/run", response_model=ApiResponse[SocialPlatformRunSummary])
def run_social_platform_ingestion(
    reset: bool = Query(default=False, description="Rebuild only V2.4 social/platform rows."),
    limit_artists: int | None = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse[SocialPlatformRunSummary]:
    """Run the mixed JSON/CSV social-platform ingestion service."""
    service = SocialPlatformService(db)
    result = service.run(reset=reset, limit_artists=limit_artists)
    return ApiResponse(
        success=True,
        message="Social and music-platform ingestion completed.",
        data=SocialPlatformRunSummary(**result),
    )


@router.get("/coverage", response_model=ApiResponse[SocialPlatformCoverage])
def get_social_platform_coverage(db: Session = Depends(get_db)) -> ApiResponse[SocialPlatformCoverage]:
    """Return coverage/freshness of imported V2.4 metrics."""
    service = SocialPlatformService(db)
    return ApiResponse(
        success=True,
        message="Social and music-platform coverage loaded.",
        data=SocialPlatformCoverage(**service.coverage()),
    )


@router.get("/artists/{artist_slug}", response_model=ApiResponse[ArtistSocialOverview])
def get_artist_social_overview(
    artist_slug: str,
    db: Session = Depends(get_db),
) -> ApiResponse[ArtistSocialOverview]:
    """Return V2.4 social/platform profiles, metrics and evidence for one artist."""
    service = SocialPlatformService(db)
    overview = service.artist_overview(artist_slug)
    if overview is None:
        raise HTTPException(status_code=404, detail=f"Artist {artist_slug} was not found.")

    return ApiResponse(
        success=True,
        message=f"Social and music-platform data loaded for artist {artist_slug}.",
        data=ArtistSocialOverview(**overview),
    )


@router.post("/lastfm/{artist_slug}/refresh", response_model=ApiResponse[LastfmRefreshResult])
def refresh_lastfm_artist(
    artist_slug: str,
    force: bool = Query(default=False, description="Refresh even when Last.fm top tracks are already cached."),
    db: Session = Depends(get_db),
) -> ApiResponse[LastfmRefreshResult]:
    """Refresh Last.fm top tracks for one artist when LASTFM_API_KEY is configured."""
    service = SocialPlatformService(db)
    result = service.refresh_lastfm_artist(artist_slug, force=force)
    if "was not found" in result["message"]:
        raise HTTPException(status_code=404, detail=result["message"])
    return ApiResponse(
        success=result["refreshed"],
        message=result["message"],
        data=LastfmRefreshResult(**result),
    )
