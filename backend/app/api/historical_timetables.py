"""V2.6 historical timetable endpoints.

These endpoints expose the normalized 2022-2025 timetable dataset and its data
quality checks. Later V2.8/V2.9 blocks will consume this layer for probable and
optimized 2026 schedules.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.historical_timetable import (
    HistoricalRoomSummary,
    HistoricalTimetableCoverage,
    HistoricalTimetableImportResult,
    HistoricalTimetableIntegrityReport,
    HistoricalTimetableSlotList,
    HistoricalTimetableYearOverview,
)
from app.services.historical_timetable_service import HistoricalTimetableService

router = APIRouter()


@router.post("/import", response_model=ApiResponse[HistoricalTimetableImportResult])
def import_historical_timetables(
    reset: bool = Query(default=True, description="Delete and rebuild only V2.6 historical timetable rows."),
    db: Session = Depends(get_db),
) -> ApiResponse[HistoricalTimetableImportResult]:
    """Import the editable V2.6 historical timetable JSON into PostgreSQL."""
    service = HistoricalTimetableService(db)
    result = service.import_seed(reset=reset)
    return ApiResponse(
        success=True,
        message="Historical timetable dataset imported.",
        data=result,
    )


@router.get("/coverage", response_model=ApiResponse[HistoricalTimetableCoverage])
def get_historical_timetable_coverage(db: Session = Depends(get_db)) -> ApiResponse[HistoricalTimetableCoverage]:
    """Return global coverage and quality counters for 2022-2025 timetables."""
    service = HistoricalTimetableService(db)
    return ApiResponse(
        success=True,
        message="Historical timetable coverage loaded.",
        data=service.coverage(),
    )


@router.get("/integrity", response_model=ApiResponse[HistoricalTimetableIntegrityReport])
def get_historical_timetable_integrity(db: Session = Depends(get_db)) -> ApiResponse[HistoricalTimetableIntegrityReport]:
    """Return integrity checks: overlaps, incomplete slots and 2025 room count."""
    service = HistoricalTimetableService(db)
    return ApiResponse(
        success=True,
        message="Historical timetable integrity report loaded.",
        data=service.integrity_report(),
    )


@router.get("/slots", response_model=ApiResponse[HistoricalTimetableSlotList])
def list_all_historical_slots(
    year: int | None = Query(default=None, description="Optional year filter."),
    event_day: str | None = Query(default=None, description="Optional day filter such as friday or saturday."),
    room: str | None = Query(default=None, description="Canonical room or historical alias."),
    artist_slug: str | None = Query(default=None, description="Optional artist slug filter."),
    only_headliners: bool = Query(default=False, description="Return only headliner slots."),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[HistoricalTimetableSlotList]:
    """Return slots across all historical years with filters."""
    service = HistoricalTimetableService(db)
    return ApiResponse(
        success=True,
        message="Historical timetable slots loaded.",
        data=service.list_slots(
            year=year,
            event_day=event_day,
            room=room,
            artist_slug=artist_slug,
            only_headliners=only_headliners,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/{year}", response_model=ApiResponse[HistoricalTimetableYearOverview])
def get_historical_timetable_year(
    year: int,
    db: Session = Depends(get_db),
) -> ApiResponse[HistoricalTimetableYearOverview]:
    """Return one historical year overview with day/room summaries."""
    service = HistoricalTimetableService(db)
    overview = service.year_overview(year)
    if overview is None:
        raise HTTPException(status_code=404, detail=f"Historical timetable {year} was not found.")
    return ApiResponse(
        success=True,
        message=f"Historical timetable overview loaded for {year}.",
        data=overview,
    )


@router.get("/{year}/slots", response_model=ApiResponse[HistoricalTimetableSlotList])
def list_historical_slots_for_year(
    year: int,
    event_day: str | None = Query(default=None, description="Optional day filter such as friday or saturday."),
    room: str | None = Query(default=None, description="Canonical room or historical alias."),
    artist_slug: str | None = Query(default=None, description="Optional artist slug filter."),
    only_headliners: bool = Query(default=False, description="Return only headliner slots."),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[HistoricalTimetableSlotList]:
    """Return slots for one historical year."""
    service = HistoricalTimetableService(db)
    return ApiResponse(
        success=True,
        message=f"Historical timetable slots loaded for {year}.",
        data=service.list_slots(
            year=year,
            event_day=event_day,
            room=room,
            artist_slug=artist_slug,
            only_headliners=only_headliners,
            limit=limit,
            offset=offset,
        ),
    )


@router.get("/{year}/rooms", response_model=ApiResponse[list[HistoricalRoomSummary]])
def list_historical_rooms_for_year(
    year: int,
    event_day: str | None = Query(default=None, description="Optional day filter such as friday or saturday."),
    db: Session = Depends(get_db),
) -> ApiResponse[list[HistoricalRoomSummary]]:
    """Return room coverage for one historical year."""
    service = HistoricalTimetableService(db)
    return ApiResponse(
        success=True,
        message=f"Historical rooms loaded for {year}.",
        data=service.rooms_for_year(year, event_day=event_day),
    )
