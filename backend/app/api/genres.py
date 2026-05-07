"""Hard dance genre endpoints.

V2.5 upgrades the previous single-genre classifier into a multi-genre layer with
main genre, secondary chips, confidence and source traceability. Existing route
shapes are kept stable for the current frontend while new V2 inspection routes
are added for coverage, rebuild and V1/V2 comparison.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.genre import (
    ClassifiedArtistGenre,
    ClassifiedArtistGenreList,
    EditionGenreDistribution,
    GenreComparisonResponse,
    GenreSeed,
    GenreTaxonomyResponse,
    MultiGenreCoverage,
    MultiGenreRebuildResult,
)
from app.services.multi_genre_service import MultiGenreClassifierService

router = APIRouter()


@router.get("", response_model=ApiResponse[list[GenreSeed]])
def list_genres(db: Session = Depends(get_db)) -> ApiResponse[list[GenreSeed]]:
    """Return V2.5 main-genre counts across all artists."""
    service = MultiGenreClassifierService(db)
    return ApiResponse(
        success=True,
        message="V2.5 multi-genre distribution loaded.",
        data=service.list_genres(),
    )


@router.get("/taxonomy", response_model=ApiResponse[GenreTaxonomyResponse])
def get_genre_taxonomy(db: Session = Depends(get_db)) -> ApiResponse[GenreTaxonomyResponse]:
    """Return the V2.5 hard-dance taxonomy."""
    service = MultiGenreClassifierService(db)
    return ApiResponse(
        success=True,
        message="V2.5 hard dance taxonomy loaded.",
        data=service.get_taxonomy(),
    )


@router.get("/v2/coverage", response_model=ApiResponse[MultiGenreCoverage])
def get_multi_genre_coverage(db: Session = Depends(get_db)) -> ApiResponse[MultiGenreCoverage]:
    """Return coverage, Unknown reduction and review counts for V2.5."""
    service = MultiGenreClassifierService(db)
    return ApiResponse(
        success=True,
        message="V2.5 multi-genre coverage loaded.",
        data=service.coverage(),
    )


@router.post("/v2/rebuild", response_model=ApiResponse[MultiGenreRebuildResult])
def rebuild_multi_genres(
    reset: bool = Query(default=True, description="Delete and rebuild only V2.5 genre rows/evidence."),
    db: Session = Depends(get_db),
) -> ApiResponse[MultiGenreRebuildResult]:
    """Persist V2.5 artist_genres rows plus traceable evidence and metrics."""
    service = MultiGenreClassifierService(db)
    result = service.rebuild(reset=reset)
    return ApiResponse(
        success=True,
        message="V2.5 multi-genre layer rebuilt.",
        data=result,
    )


@router.get("/v2/comparison", response_model=ApiResponse[GenreComparisonResponse])
def compare_v1_v2_genres(
    limit: int = Query(default=500, ge=1, le=1000),
    db: Session = Depends(get_db),
) -> ApiResponse[GenreComparisonResponse]:
    """Return V1 primary_genre_seed vs V2.5 main/secondary genre comparison."""
    service = MultiGenreClassifierService(db)
    return ApiResponse(
        success=True,
        message="V1 vs V2.5 genre comparison loaded.",
        data=service.compare_v1_v2(limit=limit),
    )


@router.get("/artists", response_model=ApiResponse[ClassifiedArtistGenreList])
def list_classified_artists(
    year: int | None = Query(default=None, description="Filter artists by Nexus edition year."),
    genre: str | None = Query(default=None, description="Filter artists by V2.5 main genre."),
    secondary_genre: str | None = Query(default=None, description="Filter artists by V2.5 secondary genre chip."),
    q: str | None = Query(default=None, description="Search by artist name or slug."),
    include_unknown: bool = Query(default=True, description="Include artists whose genre remains Unknown."),
    needs_review: bool | None = Query(default=None, description="Filter artists that need manual review."),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[ClassifiedArtistGenreList]:
    """Return V2.5 classified artists with main and secondary genre filters."""
    service = MultiGenreClassifierService(db)
    return ApiResponse(
        success=True,
        message="V2.5 classified artist genres loaded.",
        data=service.list_classified_artists(
            year=year,
            genre=genre,
            secondary_genre=secondary_genre,
            query=q,
            include_unknown=include_unknown,
            needs_review=needs_review,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/artists/{slug}", response_model=ApiResponse[ClassifiedArtistGenre])
def get_classified_artist(slug: str, db: Session = Depends(get_db)) -> ApiResponse[ClassifiedArtistGenre]:
    """Return one V2.5 artist classification by slug."""
    service = MultiGenreClassifierService(db)
    artist = service.get_artist_classification(slug)

    if artist is None:
        raise HTTPException(status_code=404, detail=f"Artist {slug} was not found.")

    return ApiResponse(success=True, message=f"Artist {slug} V2.5 genre classification loaded.", data=artist)


@router.get("/editions/{year}", response_model=ApiResponse[EditionGenreDistribution])
def get_edition_genre_distribution(
    year: int,
    db: Session = Depends(get_db),
) -> ApiResponse[EditionGenreDistribution]:
    """Return V2.5 main-genre distribution for one edition."""
    service = MultiGenreClassifierService(db)
    distribution = service.get_edition_genre_distribution(year)

    if distribution is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")

    return ApiResponse(
        success=True,
        message=f"Edition {year} V2.5 genre distribution loaded.",
        data=distribution,
    )
