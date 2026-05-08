# Roadmap position — Nexus Predictor V3

Current block: **V3.2 — Arquitectura de datos ML-ready**.

## Current status

V3.0 is closed and committed with:

```text
audit predictive core for ml first v3
```

V3.1 is closed and committed with:

```text
define continuous nexus 2026 event contract
```

V3.2 starts from the updated V3 branch after the continuous Nexus 2026 contract.
Its purpose is to create the reproducible storage foundation for future ML work:
raw snapshots, normalized metrics, datasets, features, labels, model runs and
persisted predictions.

## Active branch

```text
refactor/v3-ml-first
```

## Completed before this point

- V1 MVP complete.
- V2.0 Foundations.
- V2.1 Evidence layer.
- V2.2 Spotify real/cache.
- V2.3 External ingestion base.
- V2.4 Social/music platforms and Last.fm foundations.
- V2.5 Multi-genre classification.
- V2.6 Historical timetables 2022-2025.
- V2.7 Demand/popularity scoring model.
- V2.8 Probable 2026 timetable.
- V2.9 Optimized timetable variants.
- V2.10 Premium Next.js + TypeScript frontend.
- V2.11 Professional map and timetable UX.
- V3 roadmap ML-first created.
- V3 roadmap stack section added.
- V3.0 Predictive audit and ML-first branch guardrails.
- V3.1 Continuous Nexus 2026 event contract.

## V3.2 scope

V3.2 implements:

- `raw_sources` table.
- `raw_snapshots` table.
- `normalized_metrics` table.
- `ml_datasets` table.
- `ml_feature_snapshots` table.
- `ml_labels` table.
- `ml_model_runs` table.
- `ml_predictions` table.
- V3.2 SQLAlchemy models.
- Alembic migration.
- Pydantic schemas for inspection/debug.
- `/api/v3/ml-data/coverage` endpoint.
- `/api/v3/ml-data/contracts` endpoint.
- `/api/v3/ml-data/conventions` endpoint.
- `backend/scripts/check_v3_ml_data_foundation.py`.
- Documentation of source/confidence conventions.

## V3.2 decisions

```text
raw_payload storage: PostgreSQL JSONB
snapshot retention: no automatic deletion in V3.2
```

The project keeps snapshots conservatively during the ML research phase so later
normalization, feature engineering and training can be reproduced.

## V3.2 validation

From backend:

```powershell
alembic upgrade head
pytest tests/test_api_v3_ml_data_foundation.py
pytest
```

From repo root:

```powershell
python backend/scripts/check_v3_ml_data_foundation.py
```

Manual Swagger checks:

```text
GET /api/v3/ml-data/coverage
GET /api/v3/ml-data/contracts
GET /api/v3/ml-data/conventions
```

Expected facts:

- 8 V3.2 tables exist.
- Coverage endpoint returns all 8 tables.
- Contracts endpoint explains raw/training/prediction responsibilities.
- Conventions endpoint includes `source_type`, `confidence`, `extraction_method`, `label_type`, `model_type` and `prediction_status`.
- No model training happens in this block.

## V3.2 commit

```text
build ml ready data foundation
```

## V3.2 progress

```text
10% -> 16%
```

## Next block

After V3.2 is validated and committed, continue with:

```text
V3.3 — Identidad de artistas y entity resolution
```

Do not start ingestion or model training before V3.3 identity resolution defines
how external profiles map to canonical artists.
