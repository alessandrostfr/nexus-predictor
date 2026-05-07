# Nexus Predictor V2

V2 is the professional roadmap for Nexus Predictor: PostgreSQL, Alembic, evidence-first data, external ingestion, social/music-platform metrics, multi-genre classification, historical timetable modeling and an evidence-backed demand model.

## Current status

- V2.0 Foundations: closed.
- V2.1 Evidence layer: closed.
- V2.2 Spotify real: closed.
- V2.3 External ingestion base: closed.
- V2.4 Social networks and music platforms: closed.
- V2.5 Multi-genre classification: closed.
- V2.6 Historical timetables 2022-2025: closed.
- V2.7 Demand and popularity model: delivered in this block.

## V2.7 validation

From `backend/`:

```powershell
alembic -c alembic.ini upgrade head
python scripts/check_v2_demand_model.py
pytest tests/test_api_v2_demand_model.py
pytest
```

## V2.7 API checks

With the backend running:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/predictions/v2/2026/coverage" | ConvertTo-Json -Depth 20
Invoke-RestMethod "http://127.0.0.1:8000/api/predictions/v2/2026/artists?limit=20" | ConvertTo-Json -Depth 30
Invoke-RestMethod "http://127.0.0.1:8000/api/predictions/v2/2026/artists/project-one" | ConvertTo-Json -Depth 30
Invoke-RestMethod "http://127.0.0.1:8000/api/predictions/v2/2026/comparison?limit=30" | ConvertTo-Json -Depth 30
```
