"""Database maintenance endpoints for local development."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.database import DatabaseStatus
from app.services.database_seed_service import get_database_status, seed_database_from_json

router = APIRouter()


@router.get("/status", response_model=ApiResponse[DatabaseStatus])
def database_status(db: Session = Depends(get_db)) -> ApiResponse[DatabaseStatus]:
    """Return current SQLite seed status."""
    return ApiResponse(
        success=True,
        message="Database status loaded.",
        data=get_database_status(db),
    )


@router.post("/seed", response_model=ApiResponse[dict[str, int]])
def seed_database(db: Session = Depends(get_db)) -> ApiResponse[dict[str, int]]:
    """Rebuild SQLite seed tables from the editable JSON files."""
    result = seed_database_from_json(db, reset=True)
    return ApiResponse(
        success=True,
        message="Database was reseeded from JSON files.",
        data=result,
    )
