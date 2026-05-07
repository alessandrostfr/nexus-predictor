# Nexus Predictor V2.6 — Historical timetables 2022-2025

This block creates the first structured historical timetable layer for Nexus Predictor V2.

## Scope

V2.6 focuses only on historical timetable data:

- 2022 timetable seed.
- 2023 timetable seed.
- 2024 Friday and Saturday timetable seed.
- 2025 Friday and Saturday timetable seed.
- Room alias normalization.
- The 2025 correction to seven real Fabrik rooms.
- Headliner, warm-up, closing and special-show slot flags.
- Integrity checks for incomplete slots and impossible overlaps.

It does **not** predict the 2026 timetable and does **not** optimize schedules. Those are V2.8 and V2.9.

## 2025 room correction

The 2025 edition is normalized to these seven real rooms:

- Area 19
- Main Room
- Hangar
- Open Air
- Satelite
- Club Area
- Crystal Area

Historical aliases are preserved but normalized:

- `Rave Area Club`, `Rave Area`, `Club 360` → `Club Area`
- `New Crystal`, `Crystal`, `New Crystal Area` → `Crystal Area`
- `Satellite`, `Satélite` → `Satelite`

## New database table

`historical_timetable_slots` stores one set per row:

- year
- event_day
- festival_day
- room_name / room_slug
- observed_room_name
- artist_slug / artist_name / show_name
- start_time / end_time
- start_minutes / end_minutes
- duration_minutes
- slot_order
- slot_type
- is_headliner_slot
- is_closing_slot
- is_warmup_slot
- is_special_show
- source_name / source_url
- confidence
- extraction_method
- status
- notes

## Editable seed

The editable JSON seed lives here:

```text
backend/app/data/timetables/historical_2022_2025.json
```

The seed keeps source and confidence metadata because historical timetable images can require manual review. Future image corrections should update this JSON and then rerun the importer.

## API endpoints

```text
POST /api/historical-timetables/import?reset=true
GET  /api/historical-timetables/coverage
GET  /api/historical-timetables/integrity
GET  /api/historical-timetables/slots
GET  /api/historical-timetables/{year}
GET  /api/historical-timetables/{year}/slots
GET  /api/historical-timetables/{year}/rooms
```

Examples:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/historical-timetables/coverage" | ConvertTo-Json -Depth 20
Invoke-RestMethod "http://127.0.0.1:8000/api/historical-timetables/2025" | ConvertTo-Json -Depth 20
Invoke-RestMethod "http://127.0.0.1:8000/api/historical-timetables/2025/slots?room=New%20Crystal" | ConvertTo-Json -Depth 20
Invoke-RestMethod "http://127.0.0.1:8000/api/historical-timetables/integrity" | ConvertTo-Json -Depth 20
```

## Validation

```powershell
cd backend
alembic -c alembic.ini upgrade head
python scripts/check_v2_historical_timetables.py
pytest tests/test_api_v2_historical_timetables.py
pytest
```

Expected result:

- Historical years 2022, 2023, 2024 and 2025 exist.
- 2024 and 2025 expose Friday/Saturday.
- 2025 exposes exactly seven normalized rooms.
- `New Crystal` resolves to `Crystal Area`.
- `Rave Area Club` resolves to `Club Area`.
- Slots have artist, room, start, end, source and confidence.
- Integrity checks pass with zero impossible overlaps.

## Commit

```bash
git commit -m "structure historical timetable dataset"
```
