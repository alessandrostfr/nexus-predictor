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
- V3.2 active/delivered: ML-ready data foundation.

## V3.2 foundation

V3.2 creates the storage layer that future blocks need before training real ML:

```text
raw_sources
raw_snapshots
normalized_metrics
ml_datasets
ml_feature_snapshots
ml_labels
ml_model_runs
ml_predictions
```

This block does not train models. It prepares reproducibility.

## Data honesty rules

- Raw snapshots are evidence storage, not predictions.
- Normalized metrics are feature candidates, not model outputs.
- Labels can be confirmed, inferred or proxy; proxies must be documented.
- Model runs must store metrics before being treated as useful.
- Frontend must eventually consume `ml_predictions` via API, not fake constants.
- OR-Tools remains optimization, not ML.

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

## Operational methodology

Before each new block:

1. Review the updated repository sent by Alessandro.
2. Re-read the exact roadmap block.
3. Detect missing scope before implementation.
4. Deliver complete files and ZIP with root folder `nexus-predictor/`.
5. Provide concrete validations.
6. Suggest one English commit message.
7. Report block and total V3 progress.
