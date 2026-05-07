"""V2.3 ingestion API endpoints.

These endpoints expose local validation hooks for the external-ingestion layer.
The main flow is still CLI-first through Prefect, but API endpoints make it easy
to inspect coverage from Swagger.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.ingestion import ExternalIngestionCoverage, ExternalIngestionRunSummary
from app.services.external_ingestion_service import ExternalIngestionService

router = APIRouter()


@router.get("/external/coverage", response_model=ApiResponse[ExternalIngestionCoverage])
def get_external_ingestion_coverage(db: Session = Depends(get_db)) -> ApiResponse[ExternalIngestionCoverage]:
    """Return V2.3 coverage counts for external career and venue data."""
    service = ExternalIngestionService(db)
    return ApiResponse(
        success=True,
        message="External ingestion coverage loaded.",
        data=ExternalIngestionCoverage(**service.coverage()),
    )


@router.post("/external/run", response_model=ApiResponse[ExternalIngestionRunSummary])
def run_external_ingestion(
    reset: bool = Query(default=False, description="Rebuild only V2.3 external-ingestion rows."),
    limit_artists: int | None = Query(default=None, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ApiResponse[ExternalIngestionRunSummary]:
    """Run the deterministic V2.3 ingestion service from the API.

    The Prefect flow remains the preferred orchestration entrypoint. This route
    is a Swagger-friendly validation hook and uses the same service underneath.
    """
    service = ExternalIngestionService(db)
    result = service.run(reset=reset, limit_artists=limit_artists)
    return ApiResponse(
        success=True,
        message="External ingestion run completed.",
        data=ExternalIngestionRunSummary(**result),
    )
