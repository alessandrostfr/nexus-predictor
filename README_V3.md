# Nexus Predictor V3 — ML-first operational guide

Nexus Predictor V3 rebuilds the predictive core around real Machine Learning.
This guide is intentionally strict: heuristics, manual scoring and optimization
must never be presented as final ML.

## Current roadmap position

```text
Branch target: refactor/v3-ml-first
Last closed block: V3.0 — Auditoría crítica y nueva rama ML-first
Current block: V3.1 — Contrato real Nexus 2026 y calendario continuo
Progress after V3.1 validation and commit: 10%
Commit message: define continuous nexus 2026 event contract
```

## ML honesty rule

```text
Nothing is called ML unless it has a training dataset, features, target/proxy,
a real training step, validation metrics, model metadata and persisted predictions.
```

## V3.1 rule

Nexus 2026 must be represented as one continuous event:

```text
13/06/2026 12:00 -> 14/06/2026 06:00
Duration: 18 hours
Functional day key: nexus_day
Visible label: Evento continuo
```

Do not split 2026 into Friday/Saturday functional days. Historical editions may
keep their true multi-day structure, but 2026 predictions, timetable shells,
saturation windows and future ML features must consume the V3.1 contract.

## Naming conventions from V3 onward

- `ml_`: real trained models and persisted outputs.
- `baseline_`: honest reference models/rules.
- `heuristic_`: deterministic domain rules.
- `scoring_`: manual weighted formulas.
- `optimizer_`: OR-Tools or mathematical assignment logic.
- `evidence_`: sourced facts, snapshots and manually reviewed data.
- `feature_`: ML-ready columns built from data.
- `proxy_`: approximate target when direct labels do not exist.

## V3.1 validation

From repo root:

```powershell
python backend/scripts/check_v3_event_contract.py
```

From backend:

```powershell
alembic upgrade head
pytest tests/test_api_v3_event_contract.py
pytest
```

## Next block

After V3.1 is validated and committed, continue with:

```text
V3.2 — Arquitectura de datos ML-ready
```
