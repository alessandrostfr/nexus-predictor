"""Artist seed endpoints backed by SQLite.

The real artist enrichment block will add Spotify, Last.fm, MusicBrainz and bio
data. For now this endpoint exposes the normalized lineup-based artist index.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.sqlite_repository import SQLiteRepository
from app.schemas.artist import ArtistDetail
from app.schemas.common import ApiResponse

router = APIRouter()


@router.get("", response_model=ApiResponse[dict[str, object]])
def list_artists(
    year: int | None = Query(default=None, description="Filter artists by Nexus edition year."),
    q: str | None = Query(default=None, description="Search by artist name."),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[dict[str, object]]:
    """Return artists extracted from the researched lineup seeds."""
    repository = SQLiteRepository(db)
    return ApiResponse(
        success=True,
        message="Artist index loaded from SQLite.",
        data=repository.list_artists(year=year, query=q, limit=limit, offset=offset),
    )


@router.get("/{slug}", response_model=ApiResponse[ArtistDetail])
def get_artist(slug: str, db: Session = Depends(get_db)) -> ApiResponse[ArtistDetail]:
    """Return one artist by slug."""
    repository = SQLiteRepository(db)
    artist = repository.get_artist(slug)

    if artist is None:
        raise HTTPException(status_code=404, detail=f"Artist {slug} was not found.")

    return ApiResponse(success=True, message=f"Artist {slug} loaded.", data=artist)
