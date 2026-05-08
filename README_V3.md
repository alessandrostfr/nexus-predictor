# Nexus Predictor V3 — ML-first operational guide

Nexus Predictor V3 rebuilds the predictive core around real Machine Learning.
This guide is intentionally strict: heuristics, manual scoring and optimization
must never be presented as final ML.

## Central rule

Nothing is called ML unless it has:

- training data;
- features;
- target or documented proxy;
- a real training step such as `fit()`;
- validation metrics;
- persisted predictions;
- model/version metadata.

## Current roadmap position

- V3.0 closed: predictive audit and ML-first branch guardrails.
- V3.1 closed: continuous Nexus 2026 event contract.
- V3.2 closed: ML-ready data foundation.
- V3.3 active/delivered: artist identity resolution.

## V3.3 identity foundation

V3.3 creates the identity layer required before external ingestion:

```text
artist_master
artist_aliases
artist_identity_links
artist_identity_candidates
```

This block does not train models. It prevents future models from using Spotify,
SoundCloud, YouTube or social metrics attached to the wrong artist.

## Identity honesty rules

- Internal `nexus_seed` identity can be verified because it comes from the current dataset.
- External profiles require confidence gates before feature usage.
- Only `verified` and `high` links can become feature eligible.
- `medium`, `low`, `unknown`, `pending_review` and `rejected` links are blocked from ML features.
- Top/2026 artists require careful review for external profiles.

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

## Operational methodology

Before each new block:

1. Review the updated repository sent by Alessandro.
2. Re-read the exact roadmap block.
3. Detect missing scope before implementation.
4. Deliver complete files and ZIP with root folder `nexus-predictor/`.
5. Provide concrete validations and console endpoint checks.
6. Suggest one English commit message.
7. Report block and total V3 progress.
