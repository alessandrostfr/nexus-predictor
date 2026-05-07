# Nexus Predictor V2.0 foundations

The V2.0 foundation block introduces a dedicated V2 branch, PostgreSQL through Docker Compose, Alembic migrations and a stable package location for future Prefect pipelines.

## Official local order

```bash
git checkout -b refactor/v2-foundations
cp .env.example .env
docker compose up -d postgres
cd backend
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic -c alembic.ini upgrade head
python scripts/check_v2_foundations.py
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Why Alembic now?

The V1 MVP used SQLAlchemy models with automatic `create_all()` during startup. V2 switches to explicit migrations so database changes are traceable and reproducible when the evidence layer, Spotify data, social metrics, historical timetables and optimized schedules are added.

## Compatibility rule

The existing V1 API endpoints remain available. The first migration creates the same base tables already used by the current repositories: `editions`, `artists`, `rooms` and `dataset_meta`.
