"""Room pressure endpoints for Block 8."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.room_risk import RoomCapacityRisk, RoomRiskOverview, TimetableStatus
from app.services.room_risk_service import RoomRiskService

router = APIRouter()


@router.get("/{year}", response_model=ApiResponse[RoomRiskOverview])
def get_room_risk_overview(year: int, db: Session = Depends(get_db)) -> ApiResponse[RoomRiskOverview]:
    """Return room capacity, pressure score, heatmap and timetable status."""
    service = RoomRiskService(db)
    overview = service.get_overview(year)

    if overview is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")

    return ApiResponse(success=True, message=f"Room risk overview loaded for {year}.", data=overview)


@router.get("/{year}/rooms", response_model=ApiResponse[list[RoomCapacityRisk]])
def list_room_risks(year: int, db: Session = Depends(get_db)) -> ApiResponse[list[RoomCapacityRisk]]:
    """Return one pressure card per Fabrik music room."""
    service = RoomRiskService(db)
    rooms = service.list_rooms(year)

    if rooms is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")

    return ApiResponse(success=True, message=f"Room risk cards loaded for {year}.", data=rooms)


@router.get("/{year}/rooms/{room_slug}", response_model=ApiResponse[RoomCapacityRisk])
def get_room_risk(year: int, room_slug: str, db: Session = Depends(get_db)) -> ApiResponse[RoomCapacityRisk]:
    """Return one room pressure card by slug."""
    service = RoomRiskService(db)
    room = service.get_room(year, room_slug)

    if room is None:
        raise HTTPException(status_code=404, detail=f"Room {room_slug} was not found for edition {year}.")

    return ApiResponse(success=True, message=f"Room {room_slug} risk loaded for {year}.", data=room)


@router.get("/{year}/timetable", response_model=ApiResponse[TimetableStatus])
def get_timetable_status(year: int, db: Session = Depends(get_db)) -> ApiResponse[TimetableStatus]:
    """Return official timetable import status and JSON contract."""
    service = RoomRiskService(db)
    if service.repository.get_edition(year) is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")

    return ApiResponse(
        success=True,
        message=f"Timetable status loaded for {year}.",
        data=service.get_timetable_status(year),
    )
