# Nexus Predictor V2

V2 is the professional roadmap for Nexus Predictor: PostgreSQL, Alembic, evidence-first data, external ingestion, social/music-platform metrics and later timetable prediction/optimization.

## Current status

- V2.0 Foundations: closed.
- V2.1 Evidence layer: closed.
- V2.2 Spotify real: closed.
- V2.3 External ingestion base: closed.
- V2.4 Social networks and music platforms: current delivered block.

## V2.4 validation

From `backend/`:

```powershell
python scripts/run_social_platform_ingestion.py --reset
python scripts/check_v2_social_platforms.py
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful endpoints:

```text
GET  /api/social-platforms/status
POST /api/social-platforms/run?reset=true
GET  /api/social-platforms/coverage
GET  /api/social-platforms/artists/angerfist
POST /api/social-platforms/lastfm/angerfist/refresh?force=true
```

Optional Last.fm key in `backend/.env`:

```env
LASTFM_API_KEY=
LASTFM_TOP_TRACK_LIMIT=10
```
