# Nexus Predictor V2.3 — External ingestion base

This block introduces the first real Prefect-based ingestion layer for public external research.

## Scope

V2.3 focuses only on:

- Prefect flows and reusable ingestion tasks.
- Public-research source registry.
- Candidate career events.
- Venue/festival prestige catalog.
- External evidence and artist metrics.
- Coverage validation.

It does **not** implement social metrics, Last.fm top tracks, Beatport, 1001Tracklists or the future Next.js frontend. Those belong to later roadmap blocks.

## Main files

```text
backend/app/data/external_ingestion/external_research_seed.json
backend/app/services/external_ingestion_service.py
backend/app/pipelines/flows/external_ingestion_flow.py
backend/app/pipelines/tasks/external_ingestion_tasks.py
backend/app/api/ingestion.py
backend/scripts/run_external_ingestion.py
backend/scripts/check_v2_external_ingestion.py
```

## Run

From `backend/`:

```powershell
python scripts/run_external_ingestion.py --reset
```

Or directly as a module:

```powershell
python -m app.pipelines.flows.external_ingestion_flow --reset
```

## Validate

```powershell
python scripts/check_v2_external_ingestion.py
pytest
```

## API

```text
POST /api/ingestion/external/run?reset=true&limit_artists=10
GET  /api/ingestion/external/coverage
GET  /api/evidence/artists/angerfist
GET  /api/evidence/artists/angerfist/metrics
```

## Confidence rules

Most V2.3 career signals start as `low` confidence and `pending_review` because public pages, search targets and lineup claims can be incomplete or wrong. Manual validation can later upgrade confidence to `high` or `verified`.

This is intentional: doubtful public data is stored as evidence, not treated as truth.
