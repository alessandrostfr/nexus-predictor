"""V3.4 external-ingestion architecture endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.external_ingestion_v3 import (
    V34ArchitectureResponse,
    V34DryRunRequest,
    V34DryRunResponse,
    V34SourceListResponse,
    V34ToolEvaluationListResponse,
)
from app.services.v3_external_ingestion_architecture_service import V3ExternalIngestionArchitectureService

router = APIRouter()


@router.get("/architecture", response_model=ApiResponse[V34ArchitectureResponse])
def get_external_ingestion_architecture(db: Session = Depends(get_db)) -> ApiResponse[V34ArchitectureResponse]:
    """Return V3.4-A collector contracts, statuses and required tables."""
    service = V3ExternalIngestionArchitectureService(db)
    return ApiResponse(success=True, message="V3.4-A external ingestion architecture loaded.", data=service.architecture())


@router.get("/sources", response_model=ApiResponse[V34SourceListResponse])
def list_external_ingestion_sources(db: Session = Depends(get_db)) -> ApiResponse[V34SourceListResponse]:
    """Return the source registry without exposing credential values."""
    service = V3ExternalIngestionArchitectureService(db)
    return ApiResponse(success=True, message="V3.4-A source registry loaded.", data=service.list_sources())


@router.get("/tools", response_model=ApiResponse[V34ToolEvaluationListResponse])
def list_external_ingestion_tools(db: Session = Depends(get_db)) -> ApiResponse[V34ToolEvaluationListResponse]:
    """Return tool/API/extractor evaluation registry."""
    service = V3ExternalIngestionArchitectureService(db)
    return ApiResponse(success=True, message="V3.4-A tool evaluation registry loaded.", data=service.list_tools())


@router.post("/dry-run", response_model=ApiResponse[V34DryRunResponse])
def dry_run_external_ingestion(
    payload: V34DryRunRequest,
    db: Session = Depends(get_db),
) -> ApiResponse[V34DryRunResponse]:
    """Validate scope and source configuration without saving external data."""
    service = V3ExternalIngestionArchitectureService(db)
    return ApiResponse(success=True, message="V3.4-A dry-run completed without external calls.", data=service.dry_run(payload))
