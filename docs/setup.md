# Setup guide

This guide explains how to run Nexus Predictor from a clean checkout.

## Requirements

- Python 3.11 or newer.
- Node.js 18 or newer.
- PowerShell on Windows, or equivalent shell on macOS/Linux.
- Git.

## Backend setup

```powershell
cd backend
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

Backend URLs:

```txt
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/docs
```

## Frontend setup

```powershell
cd frontend
npm install
copy .env.example .env
npm run build
npm run dev
```

Frontend URL:

```txt
http://127.0.0.1:5173
```

## Backend environment variables

```env
APP_NAME="Nexus Predictor API"
APP_VERSION="0.9.0"
ENVIRONMENT="development"
DATABASE_URL="sqlite:///./nexus_predictor.db"
AUTO_SEED_DATABASE=true
BACKEND_CORS_ORIGINS="http://127.0.0.1:5173,http://localhost:5173"
ENABLE_EXTERNAL_ARTIST_ENRICHMENT=false
SPOTIFY_CLIENT_ID=""
SPOTIFY_CLIENT_SECRET=""
LASTFM_API_KEY=""
MUSICBRAINZ_CONTACT_EMAIL=""
```

## Frontend environment variables

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

## Troubleshooting

If the frontend shows API errors, confirm the backend is running and that `VITE_API_BASE_URL` points to `/api`.

If tests cannot import `app`, run commands from `backend/`, not from the repository root.

If CORS fails, confirm the frontend origin is included in `BACKEND_CORS_ORIGINS`.
