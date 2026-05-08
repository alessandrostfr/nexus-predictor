# Roadmap position — Nexus Predictor V3

Current block: **V3.3 — Identidad de artistas y entity resolution**.

## Current status

V3.0 is closed and committed with:

```text
audit predictive core for ml first v3
```

V3.1 is closed and committed with:

```text
define continuous nexus 2026 event contract
```

V3.2 is closed and committed with:

```text
build ml ready data foundation
```

V3.3 starts from the updated V3 branch after the ML-ready data foundation. Its
purpose is to define canonical artist identity before V3.4+ ingestion attaches
external platform metrics to artists.

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
- V3.2 ML-ready data foundation.

## V3.3 scope

V3.3 implements:

- `artist_master` table.
- `artist_aliases` table.
- `artist_identity_links` table.
- `artist_identity_candidates` table.
- Deterministic name normalization utilities.
- Seed rebuild from current artists/profile data.
- Admin review endpoint for verified/rejected decisions.
- Feature eligibility gate: only verified/high external links can feed ML features.
- Minimal frontend page at `/admin/data-review`.
- `backend/scripts/check_v3_identity_resolution.py`.
- Documentation of identity-resolution conventions.

## V3.3 decisions

```text
minimum feature confidence = verified/high
top/2026 artists = external profiles require manual review unless verified/high
```

## V3.3 validation

From backend:

```powershell
alembic upgrade head
pytest tests/test_api_v3_identity_resolution.py
pytest
```

From repo root:

```powershell
python backend/scripts/check_v3_identity_resolution.py
```

Endpoint checks from console:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v3/identity/rebuild?reset=true"
curl.exe "http://127.0.0.1:8000/api/v3/identity/coverage"
curl.exe "http://127.0.0.1:8000/api/v3/identity/artists?limit=5"
curl.exe "http://127.0.0.1:8000/api/v3/identity/candidates?status=pending_review&limit=5"
```

Expected facts:

- Canonical artists exist.
- Each artist has at least one alias.
- Internal `nexus_seed` identity links are verified.
- Low/pending/rejected external links are not feature eligible.
- Admin review can verify or reject candidates.
- No model training happens in this block.

## V3.3 commit

```text
normalize artist identity resolution
```

## V3.3 progress

```text
16% -> 22%
```

## Next block

After V3.3 is validated and committed, continue with:

```text
V3.4 — Ingesta masiva híbrida y evaluación de herramientas
```

Do not start SoundCloud/YouTube/external ingestion before V3.3 identity review
rules are in place.
