# Nexus Predictor

Nexus Predictor V2 is a Python/FastAPI + Next.js application for analysing Nexus Festival at Fabrik Madrid. It combines PostgreSQL-backed evidence, artist enrichment, multi-genre classification, demand scoring, historical timetables, probable 2026 timetable prediction and optimized non-official timetable variants.

## Current V2 status

Closed through V2.10:

- V2.0 Foundations, PostgreSQL, Docker Compose and Alembic.
- V2.1 Evidence layer and source registry.
- V2.2 Spotify integration.
- V2.3 External ingestion base.
- V2.4 Social/music-platform metrics and Last.fm top tracks.
- V2.5 Multi-genre classification.
- V2.6 Historical timetables 2022-2025.
- V2.7 Demand and popularity model.
- V2.8 Probable 2026 timetable.
- V2.9 Optimized timetable variants.
- V2.10 Premium Next.js + TypeScript frontend.

## Tech stack

Backend: Python 3.11, FastAPI, PostgreSQL, SQLAlchemy 2, Alembic, Pydantic, Prefect, pytest, scikit-learn and OR-Tools.

Frontend: Next.js, TypeScript, React, Recharts, Framer Motion, lucide-react and custom CSS/design tokens.

## Backend setup

From `backend/` with the virtual environment active:

```powershell
pip install -r requirements.txt
alembic -c alembic.ini upgrade head
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:

```text
API health: http://127.0.0.1:8000/api/health
API docs:   http://127.0.0.1:8000/docs
```

## Frontend setup

From `frontend/`:

```powershell
npm install
Copy-Item .env.example .env
npm run typecheck
npm run build
npm run dev
```

Frontend URL:

```text
http://127.0.0.1:3000
```

## Environment variables

Never commit real `.env` files. The project `.gitignore` excludes them.

Frontend example:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api
```

## Main V2 API endpoints used by the frontend

```text
GET /api/health
GET /api/evidence/coverage
GET /api/genres/v2/coverage
GET /api/predictions/v2/2026/coverage
GET /api/predictions/v2/2026/artists?limit=16
GET /api/probable-timetables/2026/coverage
GET /api/probable-timetables/2026/slots?limit=14
GET /api/optimized-timetables/2026/compare
GET /api/optimized-timetables/2026/variants/fan_experience/slots?limit=16
GET /api/social-platforms/status
```

## Data honesty

The application must keep this distinction visible:

- confirmed evidence
- inferred evidence
- predicted timetable
- optimized non-official scenarios
- future official timetable when it becomes available

V2.8 and V2.9 are not official Nexus/Fabrik schedules.
