# Nexus Predictor V2

V2 is the professional roadmap for Nexus Predictor: PostgreSQL, Alembic, evidence-first data, Spotify/Last.fm enrichment, external ingestion, social/music-platform metrics, multi-genre classification, historical timetable modeling, V2 demand scoring, probable timetable prediction, optimized timetable variants and a premium Next.js frontend.

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
- V2.9 Optimized timetable variants: closed.
- V2.10 Premium frontend with Next.js + TypeScript: delivered in this block.

## V2.10 frontend setup

From `frontend/`:

```powershell
npm install
Copy-Item .env.example .env
npm run typecheck
npm run build
npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

The frontend expects the backend at:

```text
http://127.0.0.1:8000/api
```

You can change it in `frontend/.env`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api
```

## Backend validation still required

From `backend/`:

```powershell
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## V2.10 UI scope

This block directly replaces the Vite frontend with Next.js + TypeScript and adds:

- custom CSS/design tokens, no Tailwind dependency
- premium dark Nexus/Fabrik visual identity
- mobile-first layout with bottom navigation
- demand dashboard using V2.7 endpoints
- evidence and genre dashboard using V2.1/V2.5 endpoints
- probable timetable summary using V2.8 endpoints
- optimized variants comparison using V2.9 endpoints
- clear non-official labels for predicted/optimized timetables
- loading and error states that do not require backend during `next build`

## V2.10 endpoints consumed by the frontend

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

## Official timetable status

The UI must keep this distinction visible:

```text
V2.8 probable timetable = predicted_not_official
V2.9 optimized variants = optimized_not_official
source_status = no_official_timetable_yet
```

## Next block

V2.11 — Mapa profesional y experiencia final de horarios.
