"""V3.2 ML-ready data foundation endpoints.

These endpoints are intentionally internal/debug oriented. They do not expose
raw payload contents; they show whether the storage contracts required for
future ML are present and documented.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.ml_data import MLDataConventionsResponse, MLDataCoverageResponse, MLDataTableContract
from app.services.ml_data_foundation_service import MLDataFoundationService

router = APIRouter()


@router.get("/coverage", response_model=ApiResponse[MLDataCoverageResponse])
def get_ml_data_coverage(db: Session = Depends(get_db)) -> ApiResponse[MLDataCoverageResponse]:
    """Return V3.2 ML data table counts and readiness."""
    service = MLDataFoundationService(db)
    return ApiResponse(
        success=True,
        message="V3.2 ML-ready data foundation coverage loaded.",
        data=service.coverage(),
    )


@router.get("/contracts", response_model=ApiResponse[list[MLDataTableContract]])
def get_ml_data_contracts(db: Session = Depends(get_db)) -> ApiResponse[list[MLDataTableContract]]:
    """Return the table contracts created by V3.2."""
    service = MLDataFoundationService(db)
    return ApiResponse(
        success=True,
        message="V3.2 ML-ready table contracts loaded.",
        data=service.table_contracts(),
    )


@router.get("/conventions", response_model=ApiResponse[MLDataConventionsResponse])
def get_ml_data_conventions(db: Session = Depends(get_db)) -> ApiResponse[MLDataConventionsResponse]:
    """Return source, confidence, dataset, label and model conventions."""
    service = MLDataFoundationService(db)
    return ApiResponse(
        success=True,
        message="V3.2 ML data conventions loaded.",
        data=service.conventions(),
    )
