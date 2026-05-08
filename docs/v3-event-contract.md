# V3.1 — Continuous Nexus 2026 event contract

## Purpose

V3.1 fixes the temporal structure of Nexus 2026 before any real ML training is
introduced. A model can only learn useful timetable, demand and saturation
patterns if the underlying event contract represents reality correctly.

## Contract

```text
Event: Nexus Festival 2026
Venue: Fabrik Madrid
Timezone: Europe/Madrid
Start: 13/06/2026 12:00
End: 14/06/2026 06:00
Duration: 18 hours
Functional day key: nexus_day
Visible label: Evento continuo
```

## Why this matters for ML

A wrong data contract creates wrong labels and wrong features. If we split Nexus
2026 into Friday and Saturday functional days, downstream systems could learn or
show a false structure. That would contaminate timetable placement, saturation
and attendance models.

## Tables

### `event_contracts`

Stores one row per event edition contract. V3.1 creates the 2026 contract with
start/end datetimes, duration, timezone, confidence and peak-window evidence
metadata.

### `event_time_windows`

Stores ordered one-hour windows from 12:00 to 06:00. Windows are represented by
minutes from event start, so crossing midnight does not break ordering.

## Peak windows are evidence, not labels

V3.1 may mark candidate peak/closing windows such as 00:00-03:00 or 03:00-05:00.
Those fields are not saturation truth and not ML targets. They are registered as
manual/researched evidence metadata and can later become candidate features.

## API contract

```text
GET /api/v3/events/2026/contract
```

Must return:

- `duration_hours=18`.
- `continuous_event=true`.
- `functional_day_key=nexus_day`.
- `start_label=13/06/2026 12:00`.
- `end_label=14/06/2026 06:00`.
- 18 time windows.
- boundaries from `12:00` to `06:00`.

## Validation

```powershell
python backend/scripts/check_v3_event_contract.py
cd backend
alembic upgrade head
pytest tests/test_api_v3_event_contract.py
pytest
```

## Important limitation

This block does not train ML. It only fixes the time contract needed before ML
features, labels and training datasets can be built.
