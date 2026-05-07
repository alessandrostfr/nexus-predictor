# Nexus Predictor

Nexus Predictor is a FastAPI + Next.js application for analyzing Nexus Festival at Fabrik Madrid. V1 closed as a complete MVP; V2 is the professional data and product roadmap.

## Stack

- Backend: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL.
- Pipelines: Prefect-based ingestion flows.
- Models: evidence-backed demand scoring, probable timetable generation and optimized timetable variants.
- Frontend: Next.js + TypeScript with custom cyberpunk/Fabrik-night CSS.

## Current V2 position

V2.11 delivers the professional map and timetable experience:

- Calibrated seven-room Fabrik map.
- Saturation by room and franja.
- Probable 2026 timetable comparison against three optimized variants.
- Room profiles and model explanations.

## Local validation

Backend:

```powershell
cd backend
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm audit
npm run typecheck
npm run build
npm run dev
```

Open `http://127.0.0.1:3000`.
