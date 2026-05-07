# Nexus Predictor

Nexus Predictor is a Python/FastAPI + React MVP for analysing Nexus Festival at Fabrik Madrid. It combines researched historical editions, artist metadata, hard-dance subgenre classification, interpretable demand scoring, attendance prediction and a room pressure simulation for the 2026 edition.

The project is intentionally small and local-first: editable JSON seeds remain the source of truth, FastAPI exposes the data, and React renders a minimal mobile-first dashboard.

## Current MVP status

The roadmap MVP is complete through Block 9:

- Block 0: environment, structure, Git and GitHub.
- Block 1: historical Nexus and Fabrik dataset.
- Block 2: FastAPI backend and SQLite seed layer.
- Block 3: artist enrichment foundation.
- Block 4: hard dance subgenre classification.
- Block 5: attendance and demand scoring.
- Block 6: responsive React shell.
- Block 7: dashboard, rankings and artist profiles.
- Block 8: rooms, timetable readiness and saturation risk.
- Block 9: release polish, QA documentation and deployment setup.

## Tech stack

Backend: Python 3.11+, FastAPI, SQLAlchemy, SQLite, Pydantic, pytest, pandas and scikit-learn.

Frontend: React 18, Vite, Recharts, Three.js and lucide-react.

## Quick start on Windows PowerShell

Backend terminal:

```powershell
cd "C:\Users\Alessandro\Desktop\Proyectos python\nexus-predictor\backend"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python scripts/check_environment.py
python scripts/validate_dataset.py
python scripts/generate_predictions.py --year 2026
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
cd "C:\Users\Alessandro\Desktop\Proyectos python\nexus-predictor\frontend"
npm install
copy .env.example .env
npm run build
npm run dev
```

Open:

```txt
Frontend: http://127.0.0.1:5173
Backend health: http://127.0.0.1:8000/api/health
API docs: http://127.0.0.1:8000/docs
```

You can also use the helper scripts from the project root:

```powershell
.\scripts\start_backend.ps1
.\scripts\start_frontend.ps1
.\scripts\run_release_checks.ps1
```

## Main API endpoints

```txt
GET /api/health
GET /api/editions
GET /api/editions/2026
GET /api/artists
GET /api/artist-profiles/project-one
GET /api/genres/taxonomy
GET /api/genres/editions/2026
GET /api/predictions/2026
GET /api/predictions/2026/artists?limit=20
GET /api/room-risk/2026
GET /api/room-risk/2026/timetable
```

## Environment variables

Copy the example files before running the app:

```powershell
copy backend\.env.example backend\.env
copy frontend\.env.example frontend\.env
```

Never commit real `.env` files. The project `.gitignore` excludes them.

## Data and model notes

- Historical edition data: `backend/app/data/editions/`.
- Artist enrichment cache: `backend/app/data/artists/enriched_artists.json`.
- Genre overrides: `backend/app/data/artists/genre_overrides.json`.
- Prediction snapshots: `backend/app/data/predictions/`.
- Timetable readiness: `backend/app/data/timetables/2026.json`.
- Room capacities: `backend/app/data/venue/fabrik_rooms.json`.

The current model is interpretable scoring, not a black-box ML model. This is intentional because the public dataset is small and the app needs explainable output.

## Documentation

- `docs/setup.md`: local setup and environment variables.
- `docs/data-sources.md`: data sources and confidence notes.
- `docs/model-notes.md`: scoring and room pressure explanations.
- `docs/deployment.md`: basic deployment guidance.
- `docs/mvp-checklist.md`: final release checklist.
- `docs/ROADMAP_POSITION.md`: roadmap state.
