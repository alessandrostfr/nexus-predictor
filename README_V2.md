# Nexus Predictor V2

V2 is the professional roadmap for Nexus Predictor: PostgreSQL, Alembic, evidence-first data, Spotify/Last.fm enrichment, external ingestion, social/music-platform metrics, multi-genre classification, historical timetable modeling, V2 demand scoring, probable timetable prediction and optimized timetable variants.

## Current status after this block

- V2.0 Foundations: closed.
- V2.1 Evidence layer: closed.
- V2.2 Spotify real: closed.
- V2.3 External ingestion base: closed.
- V2.4 Social networks and music platforms: closed.
- V2.5 Multi-genre classification: closed.
- V2.6 Historical timetables 2022-2025: closed.
- V2.7 Demand and popularity model: closed.
- V2.8 Probable 2026 timetable: closed.
- V2.9 Optimized timetable variants: delivered in this block.

## V2.9 validation

From `backend/`:

```powershell
pip install -r requirements.txt
alembic -c alembic.ini upgrade head
python scripts/check_v2_optimized_timetable.py
pytest tests/test_api_v2_optimized_timetable.py
pytest
```

## V2.9 endpoints

```text
POST /api/optimized-timetables/2026/rebuild?reset=true
GET  /api/optimized-timetables/2026/coverage
GET  /api/optimized-timetables/2026/variants
GET  /api/optimized-timetables/2026/compare
GET  /api/optimized-timetables/2026/slots
GET  /api/optimized-timetables/2026/variants/anti_crowding_extreme
GET  /api/optimized-timetables/2026/variants/balanced
GET  /api/optimized-timetables/2026/variants/fan_experience
GET  /api/optimized-timetables/2026/variants/fan_experience/slots?room=New%20Crystal
GET  /api/optimized-timetables/2026/variants/fan_experience/artists/project-one
GET  /api/optimized-timetables/2026/integrity
```

## Official timetable status

V2.9 variants are optimized scenarios, not the official Nexus/Fabrik timetable:

```text
official_status = optimized_not_official
source_status = no_official_timetable_yet
is_official = false
```

## Next block

V2.10 — Frontend premium: direct migration to Next.js + TypeScript.
