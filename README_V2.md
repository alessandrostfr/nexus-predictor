# Nexus Predictor V2 - setup inicial

La V2 arranca como una evolución ambiciosa del MVP V1: PostgreSQL, Alembic, FastAPI, Prefect, capa de evidencias y pipelines de ingesta.

## Bloques cerrados

- V2.0 — Foundations V2.
- V2.1 — Capa de evidencias.
- V2.2 — Spotify real.
- V2.3 — Ingesta externa base, pendiente de validación local tras aplicar este bloque.

## Validación V2.3

Desde `backend/`:

```powershell
python scripts/run_external_ingestion.py --reset
python scripts/check_v2_external_ingestion.py
pytest
```

Endpoints:

```text
POST /api/ingestion/external/run?reset=true&limit_artists=10
GET  /api/ingestion/external/coverage
GET  /api/evidence/artists/angerfist
```

## Nota sobre confianza

Los datos externos candidatos se registran con fuente, URL, fecha, confianza y notas. Si una fuente es dudosa, se marca como `low` o `pending_review`, no como verdad absoluta.
