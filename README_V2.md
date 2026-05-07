# Nexus Predictor V2

V2 is the professional roadmap for Nexus Predictor: PostgreSQL, Alembic, evidence-first data, external ingestion, social/music-platform metrics, multi-genre classification, historical timetable modeling, demand prediction and timetable intelligence.

## Current status

- V2.0 Foundations: closed.
- V2.1 Evidence layer: closed.
- V2.2 Spotify real: closed.
- V2.3 External ingestion base: closed.
- V2.4 Social networks and music platforms: closed.
- V2.5 Multi-genre classification: closed.
- V2.6 Historical timetables 2022-2025: closed.
- V2.7 Demand and popularity model: closed.
- V2.8 Probable 2026 timetable: delivered in this block.

## V2.8 validation

From `backend/`:

```powershell
alembic -c alembic.ini upgrade head
python scripts/check_v2_probable_timetable.py
pytest tests/test_api_v2_probable_timetable.py
pytest
```

## V2.8 API endpoints

```txt
POST /api/probable-timetables/2026/rebuild?reset=true
GET  /api/probable-timetables/2026/coverage
GET  /api/probable-timetables/2026
GET  /api/probable-timetables/2026/slots
GET  /api/probable-timetables/2026/rooms
GET  /api/probable-timetables/2026/integrity
GET  /api/probable-timetables/2026/artists/project-one
```

V2.8 is explicitly non-official: the official Nexus 2026 timetable has not been published. The API returns `official_available=false`, `source_status=no_official_timetable_yet` and `is_official=false` for generated slots.
