# Nexus Predictor V2.8 — Probable 2026 timetable

V2.8 generates a **probable** Nexus 2026 timetable from the data layers already closed in the roadmap:

- V2.6 historical timetables 2022-2025.
- V2.7 demand/popularity predictions.
- V2.5 multi-genre context.

This block does **not** generate optimized alternatives. That belongs to V2.9. V2.8 answers a narrower question: given past organization patterns and current demand, where and when would each 2026 artist probably be placed?

## Non-official contract

Every API payload exposes:

- `official_available: false`
- `source_status: "no_official_timetable_yet"`
- `official_status: "predicted_not_official"`
- `is_official: false` per slot

This prevents the predicted timetable from being confused with the future official Fabrik/Nexus schedule.

## Model behavior

The assignment model is intentionally interpretable:

1. It loads V2.7 demand predictions for 2026.
2. It learns compact patterns from historical timetable rows:
   - artist-room history,
   - genre-room history,
   - warm-up/headliner/closing slot structure.
3. It assigns artists to the verified seven-room Fabrik model.
4. It balances top-demand artists across Friday and Saturday.
5. It assigns the strongest artists to peak/headliner windows.
6. It stores confidence, probability and reasons for every slot.

## Main endpoints

```txt
POST /api/probable-timetables/2026/rebuild?reset=true
GET  /api/probable-timetables/2026/coverage
GET  /api/probable-timetables/2026
GET  /api/probable-timetables/2026/slots
GET  /api/probable-timetables/2026/slots?room=New%20Crystal
GET  /api/probable-timetables/2026/artists/project-one
GET  /api/probable-timetables/2026/rooms
GET  /api/probable-timetables/2026/integrity
```

## Validation

From `backend/`:

```powershell
alembic -c alembic.ini upgrade head
python scripts/check_v2_probable_timetable.py
pytest tests/test_api_v2_probable_timetable.py
pytest
```

## Commit

```txt
predict probable 2026 timetable
```
