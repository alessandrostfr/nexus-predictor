# Nexus Predictor V2.4 — Social networks and music platforms

This block adds the mixed ingestion layer for social popularity, platform presence and momentum metrics.

## Scope

V2.4 focuses on:

- Manual/curated profile registry for Instagram, TikTok, YouTube, Facebook and X/Twitter.
- Manual/curated music-platform profiles for Last.fm, SoundCloud, Apple Music, Beatport and 1001Tracklists.
- CSV import for fragile counters such as followers, engagement rate and average views.
- Optional Last.fm API refresh for top tracks when `LASTFM_API_KEY` is configured.
- Derived metrics:
  - `social.total_followers`
  - `social.platform_count`
  - `social.reach_score`
  - `social.engagement_score`
  - `social.momentum_score`
  - `platform.music_presence_score`
  - `lastfm.top_track_count` when Last.fm refresh succeeds.

## Why a mixed system?

Many social networks restrict APIs, change pages often or require manual verification. V2.4 therefore keeps a serious evidence trail instead of pretending every source is equally reliable.

- API data uses `confidence=high` only when the API call succeeds.
- Manual/CSV data starts as `medium` or `low` depending on review status.
- Search URLs or candidate profiles remain `pending_review`.
- Every imported value gets evidence with source, URL, captured date, confidence, extraction method and notes.

## Files

```text
backend/app/data/social_platforms/social_platform_seed.json
backend/app/data/social_platforms/manual_social_metrics.csv
backend/app/services/social_platform_service.py
backend/app/api/social_platforms.py
backend/app/schemas/social_platforms.py
backend/app/pipelines/flows/social_platforms_flow.py
backend/app/pipelines/tasks/social_platform_tasks.py
backend/scripts/run_social_platform_ingestion.py
backend/scripts/check_v2_social_platforms.py
backend/tests/test_api_v2_social_platforms.py
```

## Run

From `backend/`:

```powershell
python scripts/run_social_platform_ingestion.py --reset
```

Or through Prefect directly:

```powershell
python -m app.pipelines.flows.social_platforms_flow --reset
```

## Optional Last.fm top tracks

Add this to `backend/.env`:

```env
LASTFM_API_KEY=your_lastfm_key
LASTFM_TOP_TRACK_LIMIT=10
```

Then run:

```powershell
python scripts/run_social_platform_ingestion.py --lastfm angerfist --force
```

If the key is missing, the refresh fails safely and does not block the app.

## Validate

```powershell
python scripts/run_social_platform_ingestion.py --reset
python scripts/check_v2_social_platforms.py
pytest
```

API endpoints:

```text
GET  /api/social-platforms/status
POST /api/social-platforms/run?reset=true
GET  /api/social-platforms/coverage
GET  /api/social-platforms/artists/angerfist
POST /api/social-platforms/lastfm/angerfist/refresh?force=true
```

## Hotfix de seguridad para Last.fm

Los errores de Last.fm se normalizan antes de salir por CLI/API porque la API key viaja como parámetro `api_key` en la URL. Si Last.fm devuelve `403`, el sistema registra un warning seguro sin exponer la clave y mantiene operativo el resto del bloque.

La variable opcional `LASTFM_USER_AGENT` permite identificar la app ante Last.fm en llamadas locales.
