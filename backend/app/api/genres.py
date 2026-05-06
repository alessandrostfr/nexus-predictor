"""Genre seed endpoints.

Block 2 exposes only the genre labels already present in the dataset. The real
classification engine and final taxonomy are intentionally left for Block 4.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.sqlite_repository import SQLiteRepository
from app.schemas.common import ApiResponse
from app.schemas.genre import EditionGenreDistribution, GenreSeed

router = APIRouter()


@router.get("", response_model=ApiResponse[list[GenreSeed]])
def list_genres(db: Session = Depends(get_db)) -> ApiResponse[list[GenreSeed]]:
    """Return current genre seed counts across all artists."""
    repository = SQLiteRepository(db)
    return ApiResponse(
        success=True,
        message="Genre seeds loaded from artist index.",
        data=repository.list_genres(),
    )


@router.get("/editions/{year}", response_model=ApiResponse[EditionGenreDistribution])
def get_edition_genre_distribution(
    year: int,
    db: Session = Depends(get_db),
) -> ApiResponse[EditionGenreDistribution]:
    """Return genre seed distribution for one edition."""
    repository = SQLiteRepository(db)
    distribution = repository.get_edition_genres(year)

    if distribution is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")

    return ApiResponse(
        success=True,
        message=f"Edition {year} genre seed distribution loaded.",
        data=distribution,
    )
