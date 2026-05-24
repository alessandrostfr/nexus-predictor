# Nexus Predictor — Block 16.1 VPS deployment patch

Copy these files into the repository root while on branch `deploy/block-16-nexus-vps`.

Files included:

- `.gitattributes`
- `.env.production.example`
- `docker-compose.production.yml`
- `backend/Dockerfile`
- `backend/.dockerignore`
- `frontend/Dockerfile`
- `frontend/.dockerignore`
- `frontend/package.json`
- `docs/deployment/nexus-vps-runbook.md`
- `docs/deployment/scripts/backup_nexus_postgres.sh`

Before applying the patch, restore the generated `repomix-output.md` if it appears modified:

```powershell
git restore repomix-output.md
```

After applying the patch, validate locally:

```powershell
git status --short
cd backend
python -m compileall app
python -c "from app.main import app; print('backend import OK')"
cd ..\frontend
npm install
npm run typecheck
npm run build
cd ..
docker compose --env-file .env.production.example -f docker-compose.production.yml config
```

Do not commit `.env.production`.
