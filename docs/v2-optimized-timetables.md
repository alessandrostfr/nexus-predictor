# Nexus Predictor V2.9 — Optimized timetable variants

This block adds the optimized timetable layer for Nexus Predictor V2.

## Scope

V2.9 focuses only on optimized 2026 timetable variants:

- Variant A: `anti_crowding_extreme`.
- Variant B: `balanced`.
- Variant C: `fan_experience`.
- Comparable `crowding_score`, `conflict_score`, `experience_score` and `optimization_score`.
- Hard constraints for one artist per variant, one artist per room/time slot and the verified seven-room Fabrik model.
- API endpoints for rebuilding, comparing, filtering and integrity checks.

It does **not** migrate the frontend to Next.js and does **not** build the final map/timetable UI. Those belong to V2.10 and V2.11.

## Official status

All V2.9 rows are optimized scenarios:

```text
official_status = optimized_not_official
source_status = no_official_timetable_yet
is_official = false
```

The official Nexus 2026 timetable must still be treated as unavailable until a verified source is added.

## Variants

### A — Anti-aglomeraciones extremo

Prioritizes crowd-flow safety and tries to avoid severe pressure peaks in small rooms.

### B — Equilibrado

Balances crowding, conflicts and fan experience.

### C — Experiencia fan

Prioritizes sequential viewing of top artists and protects important sets from severe clashes.

## Metrics

- `crowding_score`: pressure risk. Lower is better.
- `conflict_score`: severe clash risk, especially among top artists. Lower is better.
- `experience_score`: fan-viewing quality. Higher is better.
- `optimization_score`: weighted final score for the selected variant strategy. Higher is better.

## API endpoints

```text
POST /api/optimized-timetables/{year}/rebuild?reset=true
GET  /api/optimized-timetables/{year}/coverage
GET  /api/optimized-timetables/{year}/variants
GET  /api/optimized-timetables/{year}/compare
GET  /api/optimized-timetables/{year}/slots
GET  /api/optimized-timetables/{year}/variants/{variant_key}
GET  /api/optimized-timetables/{year}/variants/{variant_key}/slots
GET  /api/optimized-timetables/{year}/variants/{variant_key}/artists/{artist_slug}
GET  /api/optimized-timetables/{year}/integrity
```

## Validation

```powershell
cd backend
pip install -r requirements.txt
alembic -c alembic.ini upgrade head
python scripts/check_v2_optimized_timetable.py
pytest tests/test_api_v2_optimized_timetable.py
pytest
```

Expected result:

- 3 variants are generated.
- Each variant has comparable metrics.
- No artist appears twice in the same variant.
- No room/time slot overlaps inside a variant.
- The output stays inside the verified seven-room Fabrik model.
```
