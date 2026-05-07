"""V2.9 optimized timetable endpoints.

These routes expose the three optimized 2026 timetable variants. They are not
official schedules and should be compared against V2.8 probable timetable rather
than treated as Fabrik/Nexus truth.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.optimized_timetable import (
    OptimizedTimetableComparison,
    OptimizedTimetableCoverage,
    OptimizedTimetableIntegrityReport,
    OptimizedTimetableRebuildResult,
    OptimizedTimetableSlotList,
    OptimizedTimetableSlotRecord,
    OptimizedTimetableVariantSummary,
    OptimizedTimetableYearOverview,
)
from app.services.optimized_timetable_service import OptimizedTimetableService, VARIANT_ORDER

router = APIRouter()


@router.post("/{year}/rebuild", response_model=ApiResponse[OptimizedTimetableRebuildResult])
def rebuild_optimized_timetables(
    year: int,
    reset: bool = Query(default=True, description="Delete and rebuild all V2.9 optimized variants for this year."),
    db: Session = Depends(get_db),
) -> ApiResponse[OptimizedTimetableRebuildResult]:
    """Generate the three optimized variants."""
    service = OptimizedTimetableService(db)
    try:
        result = service.rebuild(year, reset=reset)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse(
        success=True,
        message=f"V2.9 optimized timetable variants rebuilt for {year}. These are not official schedules.",
        data=result,
    )


@router.get("/{year}/coverage", response_model=ApiResponse[OptimizedTimetableCoverage])
def get_optimized_timetable_coverage(year: int, db: Session = Depends(get_db)) -> ApiResponse[OptimizedTimetableCoverage]:
    """Return coverage across all optimized variants."""
    service = OptimizedTimetableService(db)
    coverage = service.coverage(year)
    if coverage is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(success=True, message=f"V2.9 optimized timetable coverage loaded for {year}.", data=coverage)


@router.get("/{year}/variants", response_model=ApiResponse[list[OptimizedTimetableVariantSummary]])
def list_optimized_variants(year: int, db: Session = Depends(get_db)) -> ApiResponse[list[OptimizedTimetableVariantSummary]]:
    """Return comparable metrics for the three variants."""
    service = OptimizedTimetableService(db)
    variants = service.list_variants(year)
    if variants is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(success=True, message=f"V2.9 optimized variants loaded for {year}.", data=variants)


@router.get("/{year}/compare", response_model=ApiResponse[OptimizedTimetableComparison])
def compare_optimized_variants(year: int, db: Session = Depends(get_db)) -> ApiResponse[OptimizedTimetableComparison]:
    """Compare anti-crowding, balanced and fan-experience variants."""
    service = OptimizedTimetableService(db)
    comparison = service.compare(year)
    if comparison is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(success=True, message=f"V2.9 optimized variant comparison loaded for {year}.", data=comparison)


@router.get("/{year}/integrity", response_model=ApiResponse[OptimizedTimetableIntegrityReport])
def get_optimized_timetable_integrity(year: int, db: Session = Depends(get_db)) -> ApiResponse[OptimizedTimetableIntegrityReport]:
    """Return integrity checks for all optimized variants."""
    service = OptimizedTimetableService(db)
    if service.repository.get_edition(year) is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(success=True, message=f"V2.9 optimized timetable integrity loaded for {year}.", data=service.integrity_report(year))


@router.get("/{year}/slots", response_model=ApiResponse[OptimizedTimetableSlotList])
def list_optimized_slots(
    year: int,
    variant_key: str | None = Query(default=None, description=f"One of: {', '.join(VARIANT_ORDER)}"),
    event_day: str | None = Query(default=None, description="Optional day filter such as friday or saturday."),
    room: str | None = Query(default=None, description="Canonical room or known alias such as New Crystal."),
    artist_slug: str | None = Query(default=None, description="Optional artist slug filter."),
    only_headliners: bool = Query(default=False, description="Return only optimized headliner slots."),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[OptimizedTimetableSlotList]:
    """Return optimized slots with optional filters."""
    if variant_key is not None and variant_key not in VARIANT_ORDER:
        raise HTTPException(status_code=404, detail=f"Variant {variant_key} was not found.")
    service = OptimizedTimetableService(db)
    slots = service.list_slots(
        year,
        variant_key=variant_key,
        event_day=event_day,
        room=room,
        artist_slug=artist_slug,
        only_headliners=only_headliners,
        limit=limit,
        offset=offset,
    )
    if slots is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(success=True, message=f"V2.9 optimized timetable slots loaded for {year}.", data=slots)


@router.get("/{year}/variants/{variant_key}", response_model=ApiResponse[OptimizedTimetableYearOverview])
def get_optimized_variant(year: int, variant_key: str, db: Session = Depends(get_db)) -> ApiResponse[OptimizedTimetableYearOverview]:
    """Return one optimized variant overview."""
    service = OptimizedTimetableService(db)
    overview = service.variant_overview(year, variant_key)
    if overview is None:
        raise HTTPException(status_code=404, detail=f"Variant {variant_key} was not found for {year}.")
    return ApiResponse(success=True, message=f"V2.9 optimized variant {variant_key} loaded for {year}.", data=overview)


@router.get("/{year}/variants/{variant_key}/slots", response_model=ApiResponse[OptimizedTimetableSlotList])
def list_optimized_variant_slots(
    year: int,
    variant_key: str,
    event_day: str | None = Query(default=None),
    room: str | None = Query(default=None),
    only_headliners: bool = Query(default=False),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ApiResponse[OptimizedTimetableSlotList]:
    """Return optimized slots for one variant."""
    if variant_key not in VARIANT_ORDER:
        raise HTTPException(status_code=404, detail=f"Variant {variant_key} was not found.")
    service = OptimizedTimetableService(db)
    slots = service.list_slots(year, variant_key=variant_key, event_day=event_day, room=room, only_headliners=only_headliners, limit=limit, offset=offset)
    if slots is None:
        raise HTTPException(status_code=404, detail=f"Edition {year} was not found.")
    return ApiResponse(success=True, message=f"V2.9 optimized slots loaded for {variant_key}.", data=slots)


@router.get("/{year}/variants/{variant_key}/artists/{artist_slug}", response_model=ApiResponse[OptimizedTimetableSlotRecord])
def get_optimized_artist_slot(
    year: int,
    variant_key: str,
    artist_slug: str,
    db: Session = Depends(get_db),
) -> ApiResponse[OptimizedTimetableSlotRecord]:
    """Return one artist assignment inside one optimized variant."""
    service = OptimizedTimetableService(db)
    slot = service.get_artist_slot(year, variant_key, artist_slug)
    if slot is None:
        raise HTTPException(status_code=404, detail=f"Artist {artist_slug} was not found in {variant_key} for {year}.")
    return ApiResponse(success=True, message=f"V2.9 optimized slot loaded for {artist_slug} in {variant_key}.", data=slot)
