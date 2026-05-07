# Deployment guide

This project is optimized for local presentation first. Deployment is optional for the MVP.

## Frontend build

```powershell
cd frontend
npm install
npm run build
```

The static build is created in `frontend/dist/` and can be deployed to Vercel, Netlify, Cloudflare Pages or any static host.

Set:

```env
VITE_API_BASE_URL=https://YOUR_BACKEND_DOMAIN/api
```

## Backend deployment

FastAPI can be deployed to Render, Railway, Fly.io or a VPS.

Production command example:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

For local development, keep using:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Caveats

- SQLite is acceptable for local/demo use, but deployed backends need durable storage.
- Do not deploy real `.env` files.
- Do not enable external API refreshes without keys and rate-limit awareness.
- Keep room pressure labelled as simulation until official timetable data is imported.
