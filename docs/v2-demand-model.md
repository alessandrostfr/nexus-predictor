# Nexus Predictor V2.7 — Demand and popularity model V2

This block replaces the MVP-only demand score with an evidence-backed V2 model.

## Scope

V2.7 focuses on the exact roadmap scope:

- Feature engineering from the V2 evidence layer.
- Separate `popularity_score`, `career_score`, `momentum_score`, `nexus_affinity_score` and `demand_score`.
- Transparent explanations per artist.
- V1/V2 comparison endpoints.
- Fallback mode when external data is incomplete.

It does **not** generate a probable timetable, optimized timetable or frontend migration. Those remain V2.8, V2.9 and V2.10.

## Main feature groups

| Score | Inputs |
| --- | --- |
| Popularity | Spotify popularity/followers, Last.fm reach, social reach and music-platform presence. |
| Career | External career events, headliner signals, venue/festival prestige and international reach. |
| Momentum | Social momentum, engagement, Last.fm top tracks, recent releases and recent Nexus presence. |
| Nexus affinity | Nexus appearance count, returning-artist signal, historical timetable slots, current lineup and genre fit. |

## API endpoints

```text
POST /api/predictions/v2/2026/rebuild?reset=true
GET  /api/predictions/v2/2026/coverage
GET  /api/predictions/v2/2026/artists?limit=20
GET  /api/predictions/v2/2026/artists/project-one
GET  /api/predictions/v2/2026/comparison?limit=50
```

## Validation

From `backend/`:

```powershell
alembic -c alembic.ini upgrade head
python scripts/check_v2_demand_model.py
pytest tests/test_api_v2_demand_model.py
pytest
```

## Commit

```text
build v2 demand prediction model
```
