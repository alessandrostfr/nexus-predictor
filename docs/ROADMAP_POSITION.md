# Roadmap position — Nexus Predictor V3

Current block: **V3.0 — Auditoría crítica y nueva rama ML-first**.

## Source of truth

Before working on any block, use:

1. The latest repository sent by Alessandro.
2. The current block in the V3 roadmap.
3. The V3 operational methodology.

Do not start implementation by memory alone.

## Current status

Nexus Predictor V3 starts from the closed V2/V2.11 repository state.

V3 exists because the previous predictive core used a mixture of evidence-backed scoring, deterministic heuristics and optimization, but not a complete trained ML pipeline with datasets, targets/proxies, training runs, metrics, model artifacts and persisted model outputs.

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

## V3.0 scope

V3.0 is intentionally documentation/audit-first:

- Review current repository state.
- Review roadmap V3.0.
- Classify V2 predictive services.
- Inventory predictive endpoints.
- Identify reusable evidence/data/frontend assets.
- Identify scoring/heuristic/optimization pieces that must not be called ML.
- Create/update `README_V3.md`.
- Create/update `docs/v3-predictive-audit.md`.
- Create `docs/v3-0-closure-decisions.md`.
- Strengthen `backend/scripts/check_v3_predictive_audit.py`.
- Keep frontend and predictive runtime code unchanged.

## V3.0 validation

From repo root:

```powershell
python backend/scripts/check_v3_predictive_audit.py
```

From backend:

```powershell
pytest
```

## V3.0 commit

```text
audit predictive core for ml first v3
```

## V3.0 progress

```text
0% -> 5%
```

This progress applies only after the V3.0 validation passes and the commit is created.

## Next block

After V3.0 is validated locally and committed, continue with:

```text
V3.1 — Contrato real Nexus 2026 y calendario continuo
```

V3.1 must correct the 2026 event structure to a continuous event:

```text
13/06/2026 12:00 -> 14/06/2026 06:00
```

Do not start model training before V3.1-V3.8 have established data contracts, identity resolution, ingestion, labels/proxies and features.
