"""V3 event-contract API endpoints.

The V3.1 contract endpoint is intentionally separate from V2 timetable routes.
It exposes the functional structure that future ML and timetable services must
use when handling Nexus 2026.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.event_contract import EventContractRecord, EventContractRebuildResult, EventContractValidationReport, EventTimeWindowRecord
from app.services.event_contract_service import EventContractService

router = APIRouter()


@router.post("/{year}/contract/rebuild", response_model=ApiResponse[EventContractRebuildResult])
def rebuild_event_contract(
    year: int,
    reset: bool = Query(default=True, description="Delete and rebuild the persisted V3.1 event contract."),
    db: Session = Depends(get_db),
) -> ApiResponse[EventContractRebuildResult]:
    """Rebuild the V3.1 continuous event contract for Nexus 2026."""
    service = EventContractService(db)
    try:
        result = service.rebuild_contract(year=year, reset=reset)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse(success=True, message=f"V3.1 event contract rebuilt for {year}.", data=result)


@router.get("/{year}/contract", response_model=ApiResponse[EventContractRecord])
def get_event_contract(year: int, db: Session = Depends(get_db)) -> ApiResponse[EventContractRecord]:
    """Return the continuous event contract used by V3 ML/data layers."""
    service = EventContractService(db)
    contract = service.get_contract(year)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"Event contract {year} was not found.")
    return ApiResponse(success=True, message=f"V3.1 event contract loaded for {year}.", data=contract)


@router.get("/{year}/time-windows", response_model=ApiResponse[list[EventTimeWindowRecord]])
def list_event_time_windows(year: int, db: Session = Depends(get_db)) -> ApiResponse[list[EventTimeWindowRecord]]:
    """Return ordered one-hour windows for the continuous event."""
    service = EventContractService(db)
    if service.get_contract(year) is None and year != 2026:
        raise HTTPException(status_code=404, detail=f"Event contract {year} was not found.")
    return ApiResponse(success=True, message=f"V3.1 time windows loaded for {year}.", data=service.list_time_windows(year))


@router.get("/{year}/contract/validation", response_model=ApiResponse[EventContractValidationReport])
def validate_event_contract(year: int, db: Session = Depends(get_db)) -> ApiResponse[EventContractValidationReport]:
    """Return contract validation details for development/debugging."""
    service = EventContractService(db)
    try:
        report = service.validation_report(year)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse(success=report.valid, message=f"V3.1 event contract validation loaded for {year}.", data=report)
