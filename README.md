# Nexus Predictor

Nexus Predictor is a small Python + React application to research Nexus Festival editions, enrich artists with public music data, and estimate demand, attendance, and crowd pressure for future editions.

## Current roadmap position

Current block: `Block 2 - Backend FastAPI base`.

Closed blocks:

- `Block 0 - Environment, structure, Git and GitHub`.
- `Block 1 - Historical research and dataset foundation`.

Next block: `Block 3 - Artist enrichment`.

---

## Backend setup

### Windows PowerShell

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python scripts/validate_dataset.py
python scripts/seed_database.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend health check:

```txt
http://127.0.0.1:8000/api/health
```

Interactive API docs:

```txt
http://127.0.0.1:8000/docs
```

Useful API routes after Block 2:

```txt
GET  /api/health
GET  /api/database/status
POST /api/database/seed
GET  /api/editions
GET  /api/editions/2026
GET  /api/editions/2026/lineup
GET  /api/artists
GET  /api/artists?year=2026&q=anger
GET  /api/artists/project-one
GET  /api/venue/fabrik
GET  /api/venue/fabrik/rooms
GET  /api/genres
GET  /api/genres/editions/2026
```

---

## Frontend setup

Open another terminal from the project root:

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend URL:

```txt
http://127.0.0.1:5173
```

---

## Run backend tests

From `backend/` with the virtual environment active:

```powershell
pytest
```

---

## Git workflow

At the end of Block 2:

```bash
git add .
git commit -m "build FastAPI backend foundation"
git push
```


---

## Block 3 - Artist enrichment

Block 3 adds the backend foundation for enriched artist profiles.

### New endpoints

```txt
GET  /api/artist-profiles
GET  /api/artist-profiles/{slug}
POST /api/artist-profiles/{slug}/refresh
```

### Local validation

From `backend/` with the virtual environment active:

```bash
python scripts/validate_dataset.py
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Useful URLs:

```txt
http://127.0.0.1:8000/api/artist-profiles/angerfist
http://127.0.0.1:8000/api/artist-profiles/project-one
http://127.0.0.1:8000/api/artist-profiles?year=2026&q=project
http://127.0.0.1:8000/docs
```

### Optional external API refresh

External calls are disabled by default so the app and tests work without API keys.
To enable real refreshes, configure `.env`:

```env
ENABLE_EXTERNAL_ARTIST_ENRICHMENT=true
SPOTIFY_CLIENT_ID="your_client_id"
SPOTIFY_CLIENT_SECRET="your_client_secret"
LASTFM_API_KEY="your_lastfm_key"
MUSICBRAINZ_CONTACT_EMAIL="your_email@example.com"
```

Then refresh one artist:

```bash
python scripts/enrich_artists.py --slug angerfist --external --force
```

The local cache lives at:

```txt
backend/app/data/artists/enriched_artists.json
```
