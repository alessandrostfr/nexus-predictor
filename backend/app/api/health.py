"""Health-check endpoints used to verify that the API is running."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.services.database_seed_service import get_database_status

router = APIRouter()


@router.get("", response_model=ApiResponse[dict[str, object]])
def health_check(db: Session = Depends(get_db)) -> ApiResponse[dict[str, object]]:
    """Return API and database status for local validation and monitoring."""
    database_status = get_database_status(db)
    return ApiResponse(
        success=True,
        message="Nexus Predictor API is running.",
        data={
            "status": "ok",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "database_seeded": database_status["seeded"],
        },
    )
