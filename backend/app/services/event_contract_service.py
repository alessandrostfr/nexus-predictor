"""V3.1 event contract service.

This service owns the functional time contract for Nexus 2026. It is deliberately
small and explicit because every future ML dataset depends on this definition.
The contract says: one continuous 18-hour event from 2026-06-13 12:00 to
2026-06-14 06:00 in Europe/Madrid.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import EventContractModel, EventTimeWindowModel
from app.schemas.event_contract import (
    EventContractRebuildResult,
    EventContractRecord,
    EventContractValidationReport,
    EventTimeWindowRecord,
)
from app.services.database_seed_service import dumps_json, loads_json

NEXUS_2026_YEAR = 2026
NEXUS_2026_EVENT_KEY = "nexus-2026-continuous"
NEXUS_2026_START = datetime(2026, 6, 13, 12, 0, 0)
NEXUS_2026_END = datetime(2026, 6, 14, 6, 0, 0)
NEXUS_2026_TIMEZONE = "Europe/Madrid"
NEXUS_2026_FUNCTIONAL_DAY = "nexus_day"
NEXUS_2026_VISIBLE_LABEL = "Evento continuo"

# This is evidence metadata, not a predictive target. The windows can later be
# used as candidate features, but V3.1 does not claim that these hours are true
# saturation labels.
PEAK_WINDOW_EVIDENCE: list[dict[str, object]] = [
    {
        "key": "late_night_peak_candidate",
        "label": "00:00-03:00 · peak candidate",
        "start_time": "00:00",
        "end_time": "03:00",
        "evidence_status": "manual_domain_evidence",
        "confidence": "medium",
        "used_as": "feature_candidate_not_label",
        "notes": "Registered as researched/manual event-flow evidence. It is not a measured attendance label.",
    },
    {
        "key": "closing_pressure_candidate",
        "label": "03:00-05:00 · closing pressure candidate",
        "start_time": "03:00",
        "end_time": "05:00",
        "evidence_status": "manual_domain_evidence",
        "confidence": "medium",
        "used_as": "feature_candidate_not_label",
        "notes": "Registered as a possible closing-flow feature, not as invented saturation truth.",
    },
]


def _time_label(value: datetime) -> str:
    """Return HH:MM for an event timestamp."""
    return value.strftime("%H:%M")


def _window_key(index: int, start: datetime, end: datetime) -> str:
    """Build a stable key for one hourly event window."""
    return f"hour-{index:02d}-{_time_label(start).replace(':', '')}-{_time_label(end).replace(':', '')}"


def _slot_type_for_hour(start: datetime) -> str:
    """Classify a window as flow metadata, not as ML prediction."""
    hour = start.hour
    if 12 <= hour < 17:
        return "opening_flow"
    if 17 <= hour < 22:
        return "build_up"
    if hour in {22, 23, 0, 1, 2}:
        return "peak_candidate"
    if hour in {3, 4, 5}:
        return "closing_flow"
    return "standard"


def _is_peak_candidate(start: datetime) -> bool:
    """Mark manually evidenced peak candidate windows without making labels."""
    return start.hour in {0, 1, 2, 3, 4}


class EventContractService:
    """Create, expose and validate V3 event contracts."""

    def __init__(self, db: Session) -> None:
        """Store the request-scoped database session."""
        self.db = db

    def ensure_contract(self, year: int = NEXUS_2026_YEAR) -> EventContractModel:
        """Return an existing contract or create the default V3.1 contract."""
        contract = self.get_contract_model(year)
        if contract is not None:
            return contract
        self.rebuild_contract(year=year, reset=True)
        contract = self.get_contract_model(year)
        if contract is None:  # Defensive guard; should never happen after rebuild.
            raise RuntimeError(f"Event contract {year} could not be created.")
        return contract

    def get_contract_model(self, year: int = NEXUS_2026_YEAR) -> EventContractModel | None:
        """Return one persisted contract model if it exists."""
        return self.db.scalar(select(EventContractModel).where(EventContractModel.year == year))

    def rebuild_contract(self, year: int = NEXUS_2026_YEAR, *, reset: bool = True) -> EventContractRebuildResult:
        """Rebuild the persisted V3.1 event contract and hourly windows."""
        if year != NEXUS_2026_YEAR:
            raise ValueError("V3.1 only defines the Nexus 2026 continuous event contract.")

        if reset:
            existing = self.get_contract_model(year)
            if existing is not None:
                self.db.execute(delete(EventTimeWindowModel).where(EventTimeWindowModel.event_contract_id == existing.id))
                self.db.execute(delete(EventContractModel).where(EventContractModel.id == existing.id))
                self.db.flush()

        duration_minutes = int((NEXUS_2026_END - NEXUS_2026_START).total_seconds() // 60)
        contract = EventContractModel(
            year=year,
            event_key=NEXUS_2026_EVENT_KEY,
            name="Nexus Festival 2026",
            event_type="festival",
            venue="Fabrik Madrid",
            city="Humanes de Madrid, Madrid",
            timezone=NEXUS_2026_TIMEZONE,
            starts_at=NEXUS_2026_START,
            ends_at=NEXUS_2026_END,
            start_label="13/06/2026 12:00",
            end_label="14/06/2026 06:00",
            duration_hours=duration_minutes // 60,
            duration_minutes=duration_minutes,
            continuous_event=True,
            functional_day_key=NEXUS_2026_FUNCTIONAL_DAY,
            visible_label=NEXUS_2026_VISIBLE_LABEL,
            source_status="researched_event_contract",
            confidence="high",
            extraction_method="manual_researched_contract",
            notes=(
                "V3.1 data contract: Nexus 2026 is modelled as one continuous "
                "18-hour event. Do not split this event into Friday and Saturday "
                "functional days for 2026 predictions."
            ),
            peak_windows_json=dumps_json(PEAK_WINDOW_EVIDENCE),
            raw_json=dumps_json(
                {
                    "roadmap_block": "V3.1",
                    "contract_type": "continuous_event",
                    "start": NEXUS_2026_START.isoformat(),
                    "end": NEXUS_2026_END.isoformat(),
                    "timezone": NEXUS_2026_TIMEZONE,
                    "functional_day_key": NEXUS_2026_FUNCTIONAL_DAY,
                }
            ),
        )
        self.db.add(contract)
        self.db.flush()

        for window in self._build_default_windows(contract.id):
            self.db.add(window)

        self.db.commit()
        return EventContractRebuildResult(
            year=year,
            event_key=NEXUS_2026_EVENT_KEY,
            duration_hours=duration_minutes // 60,
            time_windows=duration_minutes // 60,
            continuous_event=True,
            start_label="13/06/2026 12:00",
            end_label="14/06/2026 06:00",
            source_status="researched_event_contract",
            warnings=[],
        )

    def get_contract(self, year: int = NEXUS_2026_YEAR) -> EventContractRecord | None:
        """Return a public contract payload."""
        if year != NEXUS_2026_YEAR:
            return None
        contract = self.ensure_contract(year)
        windows = self.list_time_windows(year)
        return self._contract_to_record(contract, windows)

    def list_time_windows(self, year: int = NEXUS_2026_YEAR) -> list[EventTimeWindowRecord]:
        """Return ordered hourly windows for one contract."""
        contract = self.ensure_contract(year)
        rows = list(
            self.db.scalars(
                select(EventTimeWindowModel)
                .where(EventTimeWindowModel.event_contract_id == contract.id)
                .order_by(EventTimeWindowModel.window_index.asc())
            ).all()
        )
        return [self._window_to_record(row) for row in rows]

    def validation_report(self, year: int = NEXUS_2026_YEAR) -> EventContractValidationReport:
        """Validate the V3.1 contract in a form useful for scripts and Swagger."""
        contract = self.ensure_contract(year)
        windows = self.list_time_windows(year)
        issues: list[str] = []

        if contract.duration_hours != 18:
            issues.append(f"duration_hours must be 18, got {contract.duration_hours}.")
        if len(windows) != 18:
            issues.append(f"time window count must be 18, got {len(windows)}.")
        if contract.start_label != "13/06/2026 12:00" or contract.end_label != "14/06/2026 06:00":
            issues.append("start/end labels do not match the V3.1 Nexus 2026 contract.")
        if any(window.functional_day_key.lower() in {"friday", "saturday"} for window in windows):
            issues.append("2026 windows must not use Friday/Saturday as functional day keys.")
        if not any(window.crosses_midnight for window in windows):
            issues.append("At least one window should cross midnight, e.g. 23:00-00:00.")
        if windows and windows[0].start_time != "12:00":
            issues.append("First time window must start at 12:00.")
        if windows and windows[-1].end_time != "06:00":
            issues.append("Last time window must end at 06:00.")

        return EventContractValidationReport(
            valid=not issues,
            year=year,
            duration_hours=contract.duration_hours,
            time_window_count=len(windows),
            starts_at=contract.starts_at.isoformat(),
            ends_at=contract.ends_at.isoformat(),
            contains_friday_saturday_split=any(window.functional_day_key.lower() in {"friday", "saturday"} for window in windows),
            crosses_midnight=any(window.crosses_midnight for window in windows),
            issues=issues,
        )

    def _build_default_windows(self, contract_id: int) -> list[EventTimeWindowModel]:
        """Build 18 one-hour windows from 12:00 to 06:00."""
        windows: list[EventTimeWindowModel] = []
        total_hours = int((NEXUS_2026_END - NEXUS_2026_START).total_seconds() // 3600)
        for index in range(total_hours):
            starts_at = NEXUS_2026_START + timedelta(hours=index)
            ends_at = starts_at + timedelta(hours=1)
            start_time = _time_label(starts_at)
            end_time = _time_label(ends_at)
            crosses_midnight = starts_at.date() != ends_at.date()
            is_peak = _is_peak_candidate(starts_at)
            windows.append(
                EventTimeWindowModel(
                    event_contract_id=contract_id,
                    year=NEXUS_2026_YEAR,
                    window_index=index,
                    window_key=_window_key(index, starts_at, ends_at),
                    label=f"{start_time}-{end_time} · {NEXUS_2026_VISIBLE_LABEL}",
                    starts_at=starts_at,
                    ends_at=ends_at,
                    start_time=start_time,
                    end_time=end_time,
                    start_minutes_from_event_start=index * 60,
                    end_minutes_from_event_start=(index + 1) * 60,
                    duration_minutes=60,
                    crosses_midnight=crosses_midnight,
                    functional_day_key=NEXUS_2026_FUNCTIONAL_DAY,
                    slot_type=_slot_type_for_hour(starts_at),
                    is_peak_window=is_peak,
                    evidence_status="manual_peak_candidate" if is_peak else "contract_window",
                    confidence="medium" if is_peak else "high",
                    notes=(
                        "Peak/closing flow candidate stored as evidence metadata, not as a measured saturation label."
                        if is_peak
                        else "Continuous event contract window."
                    ),
                    raw_json=dumps_json(
                        {
                            "start_iso": starts_at.isoformat(),
                            "end_iso": ends_at.isoformat(),
                            "minutes_from_event_start": index * 60,
                            "crosses_midnight": crosses_midnight,
                        }
                    ),
                )
            )
        return windows

    def _contract_to_record(self, contract: EventContractModel, windows: list[EventTimeWindowRecord]) -> EventContractRecord:
        """Convert an ORM contract plus windows into an API schema."""
        boundary_labels = [window.start_time for window in windows]
        if windows:
            boundary_labels.append(windows[-1].end_time)
        return EventContractRecord(
            id=contract.id,
            year=contract.year,
            event_key=contract.event_key,
            name=contract.name,
            event_type=contract.event_type,
            venue=contract.venue,
            city=contract.city,
            timezone=contract.timezone,
            starts_at=contract.starts_at,
            ends_at=contract.ends_at,
            start_label=contract.start_label,
            end_label=contract.end_label,
            duration_hours=contract.duration_hours,
            duration_minutes=contract.duration_minutes,
            continuous_event=contract.continuous_event,
            functional_day_key=contract.functional_day_key,
            visible_label=contract.visible_label,
            source_status=contract.source_status,
            confidence=contract.confidence,
            extraction_method=contract.extraction_method,
            boundary_labels=boundary_labels,
            peak_windows=loads_json(contract.peak_windows_json, []),
            time_windows=windows,
            notes=contract.notes,
        )

    @staticmethod
    def _window_to_record(row: EventTimeWindowModel) -> EventTimeWindowRecord:
        """Convert an ORM time window into an API schema."""
        return EventTimeWindowRecord(
            id=row.id,
            year=row.year,
            window_index=row.window_index,
            window_key=row.window_key,
            label=row.label,
            starts_at=row.starts_at,
            ends_at=row.ends_at,
            start_time=row.start_time,
            end_time=row.end_time,
            start_minutes_from_event_start=row.start_minutes_from_event_start,
            end_minutes_from_event_start=row.end_minutes_from_event_start,
            duration_minutes=row.duration_minutes,
            crosses_midnight=row.crosses_midnight,
            functional_day_key=row.functional_day_key,
            slot_type=row.slot_type,
            is_peak_window=row.is_peak_window,
            evidence_status=row.evidence_status,
            confidence=row.confidence,
            notes=row.notes,
        )
