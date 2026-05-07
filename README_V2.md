# Nexus Predictor V2

V2 is the professional roadmap for Nexus Predictor: PostgreSQL, Alembic, evidence-first data, external ingestion, social/music-platform metrics, multi-genre classification and historical timetable modeling.

## Current status

- V2.0 Foundations: closed.
- V2.1 Evidence layer: closed.
- V2.2 Spotify real: closed.
- V2.3 External ingestion base: closed.
- V2.4 Social networks and music platforms: closed.
- V2.5 Multi-genre classification: closed.
- V2.6 Historical timetables 2022-2025: delivered in this block.

## V2.6 validation

From `backend/`:

```powershell
alembic -c alembic.ini upgrade head
python scripts/check_v2_historical_timetables.py
pytest tests/test_api_v2_historical_timetables.py
pytest
```

With the backend running:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/historical-timetables/coverage" | ConvertTo-Json -Depth 20
Invoke-RestMethod "http://127.0.0.1:8000/api/historical-timetables/2025" | ConvertTo-Json -Depth 20
Invoke-RestMethod "http://127.0.0.1:8000/api/historical-timetables/integrity" | ConvertTo-Json -Depth 20
```

## Next block

V2.7 — Demand and popularity model V2.

Do not jump to V2.8/V2.9 timetable prediction/optimization or V2.10 frontend migration before closing V2.7.
