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
- V2.10 Premium Next.js + TypeScript frontend: closed.
- V2.11 Professional map and timetable UX: delivered in this block.

## V2.11 validation

Backend terminal:

```powershell
cd backend
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
cd frontend
npm install
npm audit
npm run typecheck
npm run build
npm run dev
```

Open:

```text
http://127.0.0.1:3000
```

## V2.11 focus

- Professional interactive Fabrik map.
- Saturation by room and hour.
- Probable timetable versus optimized variants.
- Room profiles and explanations.
- Mobile-first festival experience.

## Roadmap update

After V2.11, the user approved adding a new frontend polishing block:

```text
V2.12 — Frontend polish/refinement
```

The original release block becomes:

```text
V2.13 — QA, documentation, deploy and V2 release
```

## Commit

```text
polish interactive venue map and timetable ux
```
