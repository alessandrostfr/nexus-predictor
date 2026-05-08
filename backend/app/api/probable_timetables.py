"""V2.8 probable timetable endpoints.

The routes expose the predicted 2026 timetable while repeatedly marking it as
non-official. The official Nexus 2026 timetable can later live beside this data
without ambiguity.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.probable_timetable import (
    ProbableTimetableCoverage,
    ProbableTimetableIntegrityReport,
    ProbableTimetableRebuildResult,
    ProbableTimetableRoomSummary,
    ProbableTimetableSlotList,
    ProbableTimetableSlotRecord,
    ProbableTimetableYearOverview,
)
from app.services.probable_timetable_service import ProbableTimetableService

router = APIRouter()


@router.post("/{year}/rebuild", response_model=ApiResponse[ProbableTimetableRebuildResult])
def rebuild_probable_timetable(
    year: int,
    reset: bool = Query(default=True, description="Delete and rebuild only V2.8 probable timetable rows."),
    db: Session = Depends(get_db),
) -> ApiResponse[ProbableTimetableRebuildResult]:
    """Generate the predicted non-official timetable for one year."""
    service = ProbableTimetableService(db)
    try:
        result = service.rebuild(year, reset=reset)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse(
        success=True,
        message=f"V2.8 probable timetable rebuilt for {year}. This is not an official timetable.",
        data=result,
    )


@router.get("/{year}/coverage", response_model=ApiResponse[ProbableTimetableCoverage])
def get_probable_timetable_coverage(year: int, db: Session = Depends(get_db)) -> ApiResponse[ProbableTimetableCoverage]:
    """Return V2.8 coverage and non-official status."""
    service = ProbableTimetableService(db)
    coverage = service.coverage(year)
    if coverage is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(
        success=True,
        message=f"V2.8 probable timetable coverage loaded for {year}.",
        data=coverage,
    )


@router.get("/{year}", response_model=ApiResponse[ProbableTimetableYearOverview])
def get_probable_timetable_year(year: int, db: Session = Depends(get_db)) -> ApiResponse[ProbableTimetableYearOverview]:
    """Return the predicted timetable overview for one year."""
    service = ProbableTimetableService(db)
    overview = service.year_overview(year)
    if overview is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(
        success=True,
        message=f"V2.8 probable timetable overview loaded for {year}. This is not official.",
        data=overview,
    )


@router.get("/{year}/slots", response_model=ApiResponse[ProbableTimetableSlotList])
def list_probable_timetable_slots(
    year: int,
    event_day: str | None = Query(default=None, description="Optional functional day filter. For 2026 V3.1 use nexus_day."),
    room: str | None = Query(default=None, description="Canonical room or known alias such as New Crystal."),
    artist_slug: str | None = Query(default=None, description="Optional artist slug filter."),
    only_headliners: bool = Query(default=False, description="Return only predicted headliner slots."),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[ProbableTimetableSlotList]:
    """Return predicted 2026 slots with filters."""
    service = ProbableTimetableService(db)
    slots = service.list_slots(
        year=year,
        event_day=event_day,
        room=room,
        artist_slug=artist_slug,
        only_headliners=only_headliners,
        limit=limit,
        offset=offset,
    )
    if slots is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(
        success=True,
        message=f"V2.8 probable timetable slots loaded for {year}.",
        data=slots,
    )


@router.get("/{year}/artists/{artist_slug}", response_model=ApiResponse[ProbableTimetableSlotRecord])
def get_probable_timetable_artist_slot(
    year: int,
    artist_slug: str,
    db: Session = Depends(get_db),
) -> ApiResponse[ProbableTimetableSlotRecord]:
    """Return the predicted slot for one artist."""
    service = ProbableTimetableService(db)
    slot = service.get_artist_slot(year, artist_slug)
    if slot is None:
        raise HTTPException(status_code=404, detail=f"Artist {artist_slug} was not found in V2.8 timetable for {year}.")
    return ApiResponse(
        success=True,
        message=f"V2.8 probable timetable slot loaded for {artist_slug}. This is not official.",
        data=slot,
    )


@router.get("/{year}/rooms", response_model=ApiResponse[list[ProbableTimetableRoomSummary]])
def list_probable_timetable_rooms(
    year: int,
    event_day: str | None = Query(default=None, description="Optional functional day filter. For 2026 V3.1 use nexus_day."),
    db: Session = Depends(get_db),
) -> ApiResponse[list[ProbableTimetableRoomSummary]]:
    """Return room summaries for the predicted timetable."""
    service = ProbableTimetableService(db)
    if service.repository.get_edition(year) is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(
        success=True,
        message=f"V2.8 probable timetable rooms loaded for {year}.",
        data=service.rooms_for_year(year, event_day=event_day),
    )


@router.get("/{year}/integrity", response_model=ApiResponse[ProbableTimetableIntegrityReport])
def get_probable_timetable_integrity(year: int, db: Session = Depends(get_db)) -> ApiResponse[ProbableTimetableIntegrityReport]:
    """Return impossible-overlap and capacity sanity checks."""
    service = ProbableTimetableService(db)
    if service.repository.get_edition(year) is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(
        success=True,
        message=f"V2.8 probable timetable integrity loaded for {year}.",
        data=service.integrity_report(year),
    )