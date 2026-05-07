# Nexus Predictor V2.11 — Professional map and timetable UX

V2.11 focuses on the final visual experience for rooms and schedules. It keeps the cyberpunk/Fabrik-night identity from V2.10 and adds a more controlled venue map plus clearer timetable comparison.

## Scope

- Professional seven-room Fabrik map.
- Saturation by room and time window.
- Room profile cards with model-backed metrics.
- Probable timetable versus three optimized variants.
- Timeline/swimlane view by room and day.
- Mobile-first layout with sticky filters and bottom navigation.

## Data contract

The frontend consumes existing V2 endpoints:

```text
GET /api/probable-timetables/2026/coverage
GET /api/probable-timetables/2026/slots
GET /api/optimized-timetables/2026/coverage
GET /api/optimized-timetables/2026/compare
GET /api/optimized-timetables/2026/variants/{variant_key}/slots
```

## Saturation model display

Saturation is derived from model output fields, not decorative numbers:

- `expected_pressure_score`
- `crowding_score`
- `demand_score`
- `conflict_score`
- `experience_score`
- `room_capacity`

When raw pressure is above 100, the UI normalizes it to a 0-100 display scale while still showing raw values in detail panels. This preserves the model signal that a slot can exceed safe capacity pressure.

## Official status

All current 2026 schedules remain non-official:

```text
official_available = false
source_status = no_official_timetable_yet
is_official = false
```

The UI must not present these schedules as the official Nexus/Fabrik timetable.

## Validation

From `frontend/`:

```powershell
npm install
npm audit
npm run typecheck
npm run build
npm run dev
```

From `backend/`:

```powershell
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Manual checks:

- `Salas` map is usable and professional.
- Saturation colors are coherent and derived from model fields.
- `Horarios` compares probable against all three optimized variants.
- Mobile width has no horizontal overflow.
