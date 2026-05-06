"""Festival edition endpoints backed by SQLite."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.sqlite_repository import SQLiteRepository
from app.schemas.common import ApiResponse
from app.schemas.edition import EditionDetail, EditionLineupItem, EditionSummary

router = APIRouter()


@router.get("", response_model=ApiResponse[list[EditionSummary]])
def list_editions(db: Session = Depends(get_db)) -> ApiResponse[list[EditionSummary]]:
    """List all available festival editions from the local database."""
    repository = SQLiteRepository(db)
    return ApiResponse(
        success=True,
        message="Festival editions loaded from SQLite.",
        data=repository.list_editions(),
    )


@router.get("/{year}", response_model=ApiResponse[EditionDetail])
def get_edition(year: int, db: Session = Depends(get_db)) -> ApiResponse[EditionDetail]:
    """Return one festival edition by year."""
    repository = SQLiteRepository(db)
    edition = repository.get_edition(year)

    if edition is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")

    return ApiResponse(success=True, message=f"Edition {year} loaded.", data=edition)


@router.get("/{year}/lineup", response_model=ApiResponse[list[EditionLineupItem]])
def get_edition_lineup(year: int, db: Session = Depends(get_db)) -> ApiResponse[list[EditionLineupItem]]:
    """Return only the normalized lineup for an edition."""
    repository = SQLiteRepository(db)
    lineup = repository.get_edition_lineup(year)

    if lineup is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")

    return ApiResponse(success=True, message=f"Edition {year} lineup loaded.", data=lineup)
