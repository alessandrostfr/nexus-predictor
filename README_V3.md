# Nexus Predictor V3 — ML-first operational guide

Nexus Predictor V3 starts from the final V2/V2.11 repository state and rebuilds the predictive core around real Machine Learning.

This file is intentionally strict: it exists to prevent the project from calling heuristics, manual scoring, deterministic rules or optimization "ML" when they are not trained models.

## Current V3 starting point

```text
Branch target: refactor/v3-ml-first
Roadmap block: V3.0 — Auditoría crítica y nueva rama ML-first
Project progress after this block is validated and committed locally: 5%
Commit message: audit predictive core for ml first v3
```

V3 starts after the V3 roadmap was created and expanded with the technology stack section.

## Central rule

```text
Nothing is called ML unless it has a training dataset, features, target/proxy, a real training step, validation metrics, model metadata and persisted predictions.
```

This rule applies to backend code, scripts, database rows, API responses, documentation and frontend copy.

## What V3.0 is

V3.0 is a documentation/audit block. It creates the technical starting point for the ML-first rebuild.

It must:

1. Create/use the branch `refactor/v3-ml-first`.
2. Review the updated repository and the closed V2/V2.11 state.
3. Inventory predictive endpoints and services.
4. Classify the current predictive layer honestly.
5. Identify reusable assets.
6. Identify pieces that must be replaced, renamed or demoted to baseline/heuristic.
7. Define naming conventions for the rest of V3.
8. Record closure decisions before the commit.

## What V3.0 deliberately does not do

- It does not create ML tables yet.
- It does not train scikit-learn models.
- It does not modify the visible frontend.
- It does not rewrite demand, timetable or saturation logic yet.
- It does not remove V2 services, because some of them are useful baselines, feature sources or compatibility layers.
- It does not call OR-Tools ML.

## Current repository foundations that can be reused

The repository already contains valuable V2 foundations:

- FastAPI backend.
- PostgreSQL-oriented SQLAlchemy/Alembic data layer.
- Evidence/source tables.
- Spotify cache.
- Social/platform ingestion foundations.
- Multi-genre classification foundations.
- Historical timetable tables.
- Probable and optimized timetable outputs.
- Next.js + TypeScript frontend with Nexus/Fabrik visual identity.
- Prefect-oriented pipeline structure.
- Validation scripts and backend tests.

These are useful, but they must be reinterpreted through V3 honesty rules.

## Naming conventions from V3 onward

Use names deliberately:

| Prefix / term | Meaning | Can be shown as ML? |
| --- | --- | --- |
| `ml_` | Real trained Machine Learning component. | Yes, only if it has training + metrics + persisted predictions. |
| `baseline_` | Simple reference model or rule used to compare later ML models. | Only as baseline. |
| `heuristic_` | Rule-based logic based on domain assumptions. | No. |
| `scoring_` | Manual weighted formula. | No. |
| `optimizer_` | OR-Tools or mathematical optimization layer. | No, unless clearly described as optimization using ML outputs. |
| `evidence_` | Confirmed/manual/inferred data source. | No, it is input data. |
| `feature_` | Column/signal used by models. | No by itself. |
| `proxy_` | Approximation of a target when direct truth is unavailable. | Only as documented training target/proxy. |

## ML honesty categories

Every predictive component must be assigned one of these categories:

| Category | Definition | V3 handling |
| --- | --- | --- |
| Real ML | Uses a dataset, features, target/proxy, `fit()`, validation metrics, model metadata and persisted predictions. | Allowed to be called ML. |
| Baseline | Simple reference model or rule used as a comparison floor. | Keep, but label as baseline. |
| Scoring | Manual weighted formula. | Keep only as baseline/feature support; never call final ML. |
| Heuristic | Domain rule or deterministic approximation. | Keep only as fallback or documented assumption. |
| Optimization | OR-Tools or constraint solver assignment. | Keep for V3.14, but only with ML outputs as inputs. |
| Evidence/data | Source, metric, fact, cache, profile, timetable or manual input. | Reuse as input layer. |
| Frontend-only | UI/rendering logic that displays values. | Reuse visual shell, remove fake/predictive constants later. |

## V3.0 files

This block owns these files:

```text
README_V3.md
docs/ROADMAP_POSITION.md
docs/v3-predictive-audit.md
docs/v3-0-closure-decisions.md
backend/scripts/check_v3_predictive_audit.py
```

## How to close V3.0 locally

### 1. Confirm branch

```powershell
git branch --show-current
```

Expected:

```text
refactor/v3-ml-first
```

### 2. Record the V3 start commit

Before committing V3.0, run:

```powershell
git rev-parse HEAD
```

Copy the returned hash into:

```text
docs/v3-0-closure-decisions.md
```

Replace:

```text
V3_START_COMMIT=PENDING_REPLACE_WITH_GIT_REV_PARSE_HEAD
```

with:

```text
V3_START_COMMIT=<your-current-head-hash>
```

This is required because V3.0 must confirm exactly where V3 starts.

### 3. Run the V3.0 audit check

From the repository root:

```powershell
python backend/scripts/check_v3_predictive_audit.py
```

Expected result:

```text
V3.0 predictive audit validation passed.
```

### 4. Run backend tests

From `backend/`:

```powershell
pytest
```

### 5. Commit

Only after the check and tests pass:

```powershell
git add README_V3.md docs/ROADMAP_POSITION.md docs/v3-predictive-audit.md docs/v3-0-closure-decisions.md backend/scripts/check_v3_predictive_audit.py
git commit -m "audit predictive core for ml first v3"
```

## V3.0 closure status

V3.0 is closed only when:

- The branch is `refactor/v3-ml-first`.
- The V3 start commit is recorded.
- The public naming decision is recorded.
- The predictive endpoint inventory exists.
- The predictive service inventory exists.
- Reusable assets and replacement targets are documented.
- `python backend/scripts/check_v3_predictive_audit.py` passes.
- `pytest` passes from `backend/`.
- The commit `audit predictive core for ml first v3` exists locally.

## Next block

After V3.0 is committed, continue with:

```text
V3.1 — Contrato real Nexus 2026 y calendario continuo
```

Do not start model training before V3.1-V3.8 establish data contracts, identity resolution, ingestion, labels/proxies and features.
