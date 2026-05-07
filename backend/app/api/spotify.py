"""Spotify V2.2 API endpoints.

These routes expose safe status checks, cached artist data and controlled refresh
actions. They never expose client credentials and they return clear errors when
Spotify is not configured.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.spotify import (
    SpotifyArtistCacheRecord,
    SpotifyRefreshBatchResult,
    SpotifyRefreshResult,
    SpotifyStatus,
)
from app.services.external_http_service import ExternalServiceError
from app.services.spotify_service import SpotifyService

router = APIRouter()


@router.get("/status", response_model=ApiResponse[SpotifyStatus])
def get_spotify_status() -> ApiResponse[SpotifyStatus]:
    """Return safe public Spotify integration status."""
    service = SpotifyService()
    return ApiResponse(
        success=True,
        message="Spotify integration status loaded.",
        data=service.status(),
    )


@router.get("/artists/{artist_slug}", response_model=ApiResponse[SpotifyArtistCacheRecord | None])
def get_cached_spotify_artist(
    artist_slug: str,
    db: Session = Depends(get_db),
) -> ApiResponse[SpotifyArtistCacheRecord | None]:
    """Return the cached Spotify payload for one Nexus artist if available."""
    service = SpotifyService()
    cached = service.get_cached_artist(db, artist_slug)
    message = (
        f"Spotify cache loaded for {artist_slug}."
        if cached
        else f"No Spotify cache exists yet for {artist_slug}."
    )
    return ApiResponse(success=True, message=message, data=cached)


@router.post(
    "/artists/{artist_slug}/refresh",
    response_model=ApiResponse[SpotifyRefreshResult],
)
def refresh_spotify_artist(
    artist_slug: str,
    force: bool = Query(default=False, description="Refresh even when a Spotify cache row already exists."),
    market: str | None = Query(default=None, description="Optional Spotify market override, e.g. ES, NL or US."),
    db: Session = Depends(get_db),
) -> ApiResponse[SpotifyRefreshResult]:
    """Refresh one artist from Spotify into cache, evidence and metrics."""
    service = SpotifyService()
    try:
        result = service.refresh_artist(db, artist_slug, force=force, market=market)
    except ExternalServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if not result.configured:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result.message)

    if not result.refreshed and "was not found" in result.message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)

    return ApiResponse(
        success=result.refreshed or result.cached,
        message=result.message,
        data=result,
    )


@router.post(
    "/refresh-top-artists",
    response_model=ApiResponse[SpotifyRefreshBatchResult],
)
def refresh_top_spotify_artists(
    limit: int = Query(default=10, ge=1, le=50, description="Number of artists ordered by Nexus appearances."),
    force: bool = Query(default=False, description="Refresh artists even when cached."),
    db: Session = Depends(get_db),
) -> ApiResponse[SpotifyRefreshBatchResult]:
    """Refresh several top Nexus artists from Spotify."""
    service = SpotifyService()
    if not service.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Spotify credentials are missing.",
        )

    result = service.refresh_top_artists(db, limit=limit, force=force)
    return ApiResponse(
        success=result.failed == 0,
        message="Spotify batch refresh completed.",
        data=result,
    )
