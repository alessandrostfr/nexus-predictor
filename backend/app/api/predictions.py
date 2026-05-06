"""Prediction endpoints for attendance and artist demand."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.prediction import ArtistDemandPrediction, ArtistDemandPredictionList, EditionPrediction
from app.services.prediction_service import PredictionService

router = APIRouter()


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
