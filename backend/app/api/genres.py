"""Hard dance subgenre classification endpoints.

Block 4 replaces the temporary seed-only genre endpoints with the real MVP
classifier. The implementation remains deterministic and local: manual overrides
win first, then curated seeds, then keyword rules, and finally Unknown.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.genre import (
    ClassifiedArtistGenre,
    ClassifiedArtistGenreList,
    EditionGenreDistribution,
    GenreSeed,
    GenreTaxonomyResponse,
)
from app.services.genre_classifier import GenreClassifierService

router = APIRouter()


@router.get("", response_model=ApiResponse[list[GenreSeed]])
def list_genres(db: Session = Depends(get_db)) -> ApiResponse[list[GenreSeed]]:
    """Return classified genre counts across all artists.

    The route shape is kept compatible with Block 2, but the values now come
    from the Block 4 classifier rather than from raw primary_genre_seed counts.
    """
    service = GenreClassifierService(db)
    return ApiResponse(
        success=True,
        message="Classified hard dance genres loaded.",
        data=service.list_genres(),
    )


@router.get("/taxonomy", response_model=ApiResponse[GenreTaxonomyResponse])
def get_genre_taxonomy(db: Session = Depends(get_db)) -> ApiResponse[GenreTaxonomyResponse]:
    """Return the closed MVP hard dance taxonomy."""
    service = GenreClassifierService(db)
    return ApiResponse(
        success=True,
        message="Hard dance MVP taxonomy loaded.",
        data=service.get_taxonomy(),
    )


@router.get("/artists", response_model=ApiResponse[ClassifiedArtistGenreList])
def list_classified_artists(
    year: int | None = Query(default=None, description="Filter classified artists by Nexus edition year."),
    genre: str | None = Query(default=None, description="Filter artists by classified main genre."),
    q: str | None = Query(default=None, description="Search by artist name."),
    include_unknown: bool = Query(default=True, description="Include artists whose genre remains Unknown."),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[ClassifiedArtistGenreList]:
    """Return classified artists with filters for the frontend and future model."""
    service = GenreClassifierService(db)
    return ApiResponse(
        success=True,
        message="Classified artist genres loaded.",
        data=service.list_classified_artists(
            year=year,
            genre=genre,
            query=q,
            include_unknown=include_unknown,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/artists/{slug}", response_model=ApiResponse[ClassifiedArtistGenre])
def get_classified_artist(slug: str, db: Session = Depends(get_db)) -> ApiResponse[ClassifiedArtistGenre]:
    """Return one artist classification by slug."""
    service = GenreClassifierService(db)
    artist = service.get_artist_classification(slug)

    if artist is None:
        raise HTTPException(status_code=404, detail=f"Artist {slug} was not found.")

    return ApiResponse(success=True, message=f"Artist {slug} genre classification loaded.", data=artist)


@router.get("/editions/{year}", response_model=ApiResponse[EditionGenreDistribution])
def get_edition_genre_distribution(
    year: int,
    db: Session = Depends(get_db),
) -> ApiResponse[EditionGenreDistribution]:
    """Return classified genre distribution for one edition."""
    service = GenreClassifierService(db)
    distribution = service.get_edition_genre_distribution(year)

    if distribution is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")

    return ApiResponse(
        success=True,
        message=f"Edition {year} classified genre distribution loaded.",
        data=distribution,
    )
