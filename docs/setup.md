# Setup local — Nexus Predictor

Esta guía explica cómo arrancar Nexus Predictor desde cero en local.

## Requisitos

- Python 3.11.
- Node.js 18 o superior.
- Docker Desktop.
- Git.
- PowerShell en Windows.

## 1. Clonar el proyecto

```powershell
git clone https://github.com/alessandrostfr/nexus-predictor.git
cd nexus-predictor
```

## 2. Levantar PostgreSQL

El proyecto usa PostgreSQL en Docker para el entorno local.

```powershell
docker compose up -d
docker compose ps
```

Resultado esperado:

```text
nexus_predictor_postgres ... healthy
```

Variables por defecto del `docker-compose.yml`:

```env
POSTGRES_DB=nexus_predictor
POSTGRES_USER=nexus
POSTGRES_PASSWORD=nexus
POSTGRES_PORT=5432
```

## 3. Backend

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
```

Comprueba que `backend/.env` contiene una URL compatible con PostgreSQL local:

```env
DATABASE_URL=postgresql+psycopg://nexus:nexus@localhost:5432/nexus_predictor
```

Ejecuta migraciones y validaciones:

```powershell
alembic upgrade head
pytest
```

Arranca la API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

URLs backend:

```text
http://127.0.0.1:8000/api/health
http://127.0.0.1:8000/docs
```

Comprobación rápida:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health | ConvertTo-Json -Depth 30
```

## 4. Frontend

En otra terminal:

```powershell
cd frontend
npm install
copy .env.example .env.local
npm run typecheck
npm run build
npm run dev
```

Variable esperada en `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api
```

URL frontend:

```text
http://127.0.0.1:3000
```

## 5. Validaciones V3 recomendadas

Desde `backend/` y con el virtualenv activo:

```powershell
python scripts/check_v3_predictive_audit.py
python scripts/check_v3_event_contract.py
python scripts/check_v3_ml_data_foundation.py
python scripts/check_v3_identity_resolution.py
python scripts/check_v3_external_ingestion_architecture.py
python scripts/check_v3_external_credentials.py
```

## 6. Credenciales externas opcionales

Las APIs externas son opcionales en desarrollo. No subas nunca `backend/.env` al repositorio.

Variables disponibles:

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
LASTFM_API_KEY=
YOUTUBE_API_KEY=
SOUNDCLOUD_CLIENT_ID=
SOUNDCLOUD_CLIENT_SECRET=
MUSICBRAINZ_USER_AGENT=NexusPredictorV3/0.1 (local educational ML project; contact: your-email@example.com)
```

## 7. Troubleshooting

### El backend no conecta con PostgreSQL

Comprueba Docker:

```powershell
docker compose ps
docker compose logs postgres
```

### FastAPI no importa `app`

Ejecuta los comandos desde `backend/`, no desde la raíz.

### El frontend no conecta con la API

Confirma que:

- backend está en `http://127.0.0.1:8000`;
- `NEXT_PUBLIC_API_BASE_URL` termina en `/api`;
- `BACKEND_CORS_ORIGINS` incluye `http://127.0.0.1:3000`.

### Las APIs externas no devuelven datos

Es normal si no hay credenciales. El proyecto debe reportar estados como `not_configured` o `access_unconfirmed`, no fallar silenciosamente.
