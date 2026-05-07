"""Prediction endpoints for attendance and artist demand.

V2.7 adds evidence-backed demand-model endpoints under `/predictions/v2/...`
while keeping the original MVP endpoints stable for the current frontend.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.prediction import (
    ArtistDemandPrediction,
    ArtistDemandPredictionList,
    EditionPrediction,
    V2DemandModelCoverage,
    V2DemandPrediction,
    V2DemandPredictionList,
    V2DemandRebuildResult,
    V2ModelComparisonResponse,
)
from app.services.demand_model_service import DemandModelService
from app.services.prediction_service import PredictionService

router = APIRouter()


@router.post("/v2/{year}/rebuild", response_model=ApiResponse[V2DemandRebuildResult])
def rebuild_v2_demand_model(
    year: int,
    reset: bool = Query(default=True, description="Delete and rebuild persisted V2.7 rows for this year."),
    db: Session = Depends(get_db),
) -> ApiResponse[V2DemandRebuildResult]:
    """Rebuild the V2.7 demand model for one edition."""
    service = DemandModelService(db)
    try:
        result = service.rebuild(year, reset=reset)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse(success=True, message=f"V2.7 demand model rebuilt for {year}.", data=result)


@router.get("/v2/{year}/coverage", response_model=ApiResponse[V2DemandModelCoverage])
def get_v2_demand_model_coverage(year: int, db: Session = Depends(get_db)) -> ApiResponse[V2DemandModelCoverage]:
    """Return V2.7 feature coverage counters."""
    service = DemandModelService(db)
    coverage = service.coverage(year)
    if coverage is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(success=True, message=f"V2.7 demand-model coverage loaded for {year}.", data=coverage)


@router.get("/v2/{year}/artists", response_model=ApiResponse[V2DemandPredictionList])
def list_v2_artist_predictions(
    year: int,
    genre: str | None = Query(default=None, description="Filter by V2.5 main genre."),
    q: str | None = Query(default=None, description="Search by artist name or slug."),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[V2DemandPredictionList]:
    """Return ranked V2.7 demand predictions."""
    service = DemandModelService(db)
    predictions = service.list_predictions(year, genre=genre, query=q, limit=limit, offset=offset)
    if predictions is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(success=True, message=f"V2.7 artist demand ranking loaded for {year}.", data=predictions)


@router.get("/v2/{year}/artists/{slug}", response_model=ApiResponse[V2DemandPrediction])
def get_v2_artist_prediction(year: int, slug: str, db: Session = Depends(get_db)) -> ApiResponse[V2DemandPrediction]:
    """Return one V2.7 demand prediction with feature explanations."""
    service = DemandModelService(db)
    prediction = service.get_prediction(year, slug)
    if prediction is None:
        raise HTTPException(status_code=404, detail=f"Artist {slug} was not found in V2.7 predictions for {year}.")
    return ApiResponse(success=True, message=f"V2.7 demand prediction loaded for {slug} in {year}.", data=prediction)


@router.get("/v2/{year}/comparison", response_model=ApiResponse[V2ModelComparisonResponse])
def compare_v1_v2_predictions(
    year: int,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> ApiResponse[V2ModelComparisonResponse]:
    """Return V1/V2 score comparison for one edition."""
    service = DemandModelService(db)
    comparison = service.compare_v1_v2(year, limit=limit)
    if comparison is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(success=True, message=f"V1/V2 demand comparison loaded for {year}.", data=comparison)


@router.get("/{year}", response_model=ApiResponse[EditionPrediction])
def get_edition_prediction(
    year: int,
    artist_limit: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ApiResponse[EditionPrediction]:
    """Return attendance forecast and top artist demand predictions."""
    service = PredictionService(db)
    prediction = service.get_edition_prediction(year, artist_limit=artist_limit)

    if prediction is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")

    return ApiResponse(
        success=True,
        message=f"Edition {year} prediction loaded.",
        data=prediction,
    )


@router.get("/{year}/artists", response_model=ApiResponse[ArtistDemandPredictionList])
def list_artist_predictions(
    year: int,
    genre: str | None = Query(default=None, description="Filter by classified main genre."),
    q: str | None = Query(default=None, description="Search by artist name."),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[ArtistDemandPredictionList]:
    """Return ranked demand predictions for artists in one edition."""
    service = PredictionService(db)
    predictions = service.list_artist_predictions(year, genre=genre, query=q, limit=limit, offset=offset)

    if predictions is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")

    return ApiResponse(
        success=True,
        message=f"Edition {year} artist demand ranking loaded.",
        data=predictions,
    )


@router.get("/{year}/artists/{slug}", response_model=ApiResponse[ArtistDemandPrediction])
def get_artist_prediction(
    year: int,
    slug: str,
    db: Session = Depends(get_db),
) -> ApiResponse[ArtistDemandPrediction]:
    """Return one artist demand prediction by slug."""
    service = PredictionService(db)
    prediction = service.get_artist_prediction(year, slug)

    if prediction is None:
        raise HTTPException(status_code=404, detail=f"Artist {slug} was not found in edition {year}.")

    return ApiResponse(
        success=True,
        message=f"Artist {slug} demand prediction loaded for {year}.",
        data=prediction,
    )
