"""Venue data endpoints backed by SQLite."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.sqlite_repository import SQLiteRepository
from app.schemas.common import ApiResponse
from app.schemas.venue import RoomSummary, VenueDetail

router = APIRouter()


@router.get("/fabrik", response_model=ApiResponse[VenueDetail])
def get_fabrik_venue(db: Session = Depends(get_db)) -> ApiResponse[VenueDetail]:
    """Return Fabrik room and capacity seed data."""
    repository = SQLiteRepository(db)
    return ApiResponse(
        success=True,
        message="Fabrik venue data loaded from SQLite.",
        data=repository.get_venue(),
    )


@router.get("/fabrik/rooms", response_model=ApiResponse[list[RoomSummary]])
def list_fabrik_rooms(db: Session = Depends(get_db)) -> ApiResponse[list[RoomSummary]]:
    """Return only Fabrik rooms sorted by estimated capacity."""
    repository = SQLiteRepository(db)
    return ApiResponse(
        success=True,
        message="Fabrik rooms loaded from SQLite.",
        data=repository.list_rooms(),
    )
