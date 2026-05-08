# V3.0 Predictive audit — Nexus Predictor V3

## Executive verdict

Nexus Predictor V3 starts from a useful V2/V2.11 codebase, but the current predictive core must not be considered final Machine Learning.

The repository contains strong foundations for evidence, ingestion, historical timetables, Spotify cache, genres, room data, probable timetable generation, optimized timetable generation and a premium Next.js frontend. However, the central predictive behavior is still mostly scoring, heuristic assignment and optimization. These pieces are valuable, but they must be renamed, demoted or reused as baselines/features until V3 trains real models.

## Audit source and scope

This audit covers the current repository state at the start of V3.0.

Audited areas:

- Backend API routes.
- Backend predictive/domain services.
- Data seeds and JSON datasets.
- PostgreSQL/Alembic models and migration history.
- Prefect pipeline structure.
- V2 documentation.
- Frontend architecture and visual shell.
- Validation scripts and tests.

V3.0 does not modify runtime prediction behavior. It only documents what exists and creates guardrails for the rebuild.

## ML honesty rule

```text
Nothing is called ML unless it has a training dataset, features, target/proxy, a real training step, validation metrics, model metadata and persisted predictions.
```

Current V2 predictive code does not fully satisfy that rule. Therefore, no current V2 predictive service is treated as final V3 ML.

## Classification categories

| Category | Meaning | Can it be called ML? |
| --- | --- | --- |
| Real ML | Trained model with dataset, features, target/proxy, `fit()`, validation metrics, model metadata and persisted predictions. | Yes. |
| Baseline | Reference model/rule to compare future ML against. | Only as baseline. |
| Scoring | Manual weighted formula or score components. | No. |
| Heuristic | Deterministic domain rule or approximation. | No. |
| Optimization | Solver/constraint assignment such as OR-Tools or schedule optimization. | No. |
| Evidence/data | Facts, snapshots, source registry, cache, metrics, profiles or historical data. | No; it is input. |
| Frontend-only | UI rendering, copy, filters or display layer. | No. |

## Predictive endpoint inventory

| Endpoint area | Representative routes | Current classification | V3 decision |
| --- | --- | --- | --- |
| Legacy attendance/prediction | `/api/predictions/{year}`, `/api/predictions/{year}/artists`, `/api/predictions/{year}/artists/{slug}` | Heuristic/scoring output. | Keep only as legacy compatibility/baseline reference until replaced by `/api/ml/...`. |
| V2 demand predictions | `/api/predictions/v2/{year}/rebuild`, `/api/predictions/v2/{year}/coverage`, `/api/predictions/v2/{year}/artists`, `/api/predictions/v2/{year}/artists/{slug}`, `/api/predictions/v2/{year}/comparison` | Evidence-backed scoring/baseline candidate, not final ML. | Reuse features/explanations where useful; later replace with trained artist demand ML model. |
| Probable timetables | `/api/probable-timetables/{year}/rebuild`, `/api/probable-timetables/{year}`, `/api/probable-timetables/{year}/slots`, `/api/probable-timetables/{year}/artists/{artist_slug}`, `/api/probable-timetables/{year}/rooms`, `/api/probable-timetables/{year}/integrity` | Heuristic placement using patterns and demand score. | Keep as baseline/prototype; replace with trained placement ML in V3.11. |
| Optimized timetables | `/api/optimized-timetables/{year}/rebuild`, `/api/optimized-timetables/{year}/variants`, `/api/optimized-timetables/{year}/compare`, `/api/optimized-timetables/{year}/slots`, `/api/optimized-timetables/{year}/variants/{variant_key}` | Optimization/heuristic solver layer. | Keep for V3.14, but only use ML outputs as inputs later. |
| Room risk | `/api/room-risk/{year}`, `/api/room-risk/{year}/rooms`, `/api/room-risk/{year}/rooms/{room_slug}`, `/api/room-risk/{year}/timetable` | Heuristic saturation/risk approximation. | Rebuild into trained saturation/heatmap model in V3.12. |
| Historical timetables | `/api/historical-timetables/import`, `/api/historical-timetables/coverage`, `/api/historical-timetables/integrity`, `/api/historical-timetables/slots`, `/api/historical-timetables/{year}` | Evidence/data. | Reuse as labels/features for placement and saturation datasets. |
| Evidence layer | `/api/evidence/coverage`, `/api/evidence/import-v1`, `/api/evidence/sources`, `/api/evidence/artists/{artist_slug}`, `/api/evidence/manual` | Evidence/data. | Reuse strongly; expand in V3.2-V3.8. |
| Spotify | `/api/spotify/status`, `/api/spotify/artists/{artist_slug}`, `/api/spotify/artists/{artist_slug}/refresh`, `/api/spotify/refresh-top-artists` | Evidence/data integration. | Reuse as one artist popularity source. |
| Genres | `/api/genres`, `/api/genres/taxonomy`, `/api/genres/v2/coverage`, `/api/genres/v2/rebuild`, `/api/genres/artists` | Evidence/feature engineering candidate. | Reuse as genre features, but not predictive model output. |
| External/social ingestion | `/api/ingestion/external/coverage`, `/api/ingestion/external/run`, `/api/social-platforms/...` | Evidence/data ingestion. | Reuse/expand after source/tool evaluation. |

## Predictive service inventory

| Service/file | Current role | Classification | V3 action |
| --- | --- | --- | --- |
| `backend/app/services/scoring_service.py` | Shared scoring formulas and score components. | Scoring. | Rename/reinterpret as `scoring_` or baseline support; do not call ML. |
| `backend/app/services/prediction_service.py` | Legacy attendance and artist demand prediction from deterministic logic. | Heuristic/scoring. | Keep temporarily as baseline reference; replace with trained ML APIs later. |
| `backend/app/services/demand_model_service.py` | V2.7 evidence-backed artist demand ranking with weighted factors. | Scoring/baseline candidate. | Convert concepts into features/baselines; replace with trained model in V3.10. |
| `backend/app/services/probable_timetable_service.py` | Generates probable timetable assignments from demand and historical rules. | Heuristic/baseline candidate. | Keep as baseline; replace placement logic with trained classifiers in V3.11. |
| `backend/app/services/optimized_timetable_service.py` | Creates optimized timetable variants. | Optimization/heuristic fallback. | Keep for V3.14, but feed it ML predictions later. |
| `backend/app/services/room_risk_service.py` | Computes room pressure and heatmap-like risk. | Heuristic/scoring. | Replace with trained saturation model in V3.12. |
| `backend/app/services/historical_timetable_service.py` | Imports/exposes historical slots. | Evidence/data. | Reuse for labels/features. |
| `backend/app/services/evidence_service.py` | Exposes evidence, metrics and sources. | Evidence/data. | Reuse and expand. |
| `backend/app/services/evidence_seed_service.py` | Imports seed evidence. | Evidence/data. | Reuse, but improve source confidence conventions later. |
| `backend/app/services/spotify_service.py` | Spotify cache/profile integration. | Evidence/data. | Reuse as feature source. |
| `backend/app/services/external_ingestion_service.py` | Deterministic external ingestion seed/service. | Evidence/data ingestion. | Reuse structure; expand source/tool registry in V3.4. |
| `backend/app/services/multi_genre_service.py` | Multi-genre classification layer. | Evidence/feature engineering candidate. | Reuse as categorical features; validate labels/confidence later. |
| `backend/app/services/artist_enrichment_service.py` | Local/external artist profile enrichment. | Evidence/data. | Reuse and strengthen entity resolution. |
| `backend/app/services/musicbrainz_service.py` | MusicBrainz profile lookup. | Evidence/data. | Reuse after identity confidence rules are added. |

## Backend audit

### Reusable backend pieces

- FastAPI router structure.
- Existing route modules and response pattern.
- SQLAlchemy/Alembic setup.
- Evidence/source tables.
- Artist, edition and room seed repositories.
- Spotify cache table and service.
- Historical timetable table and service.
- Existing scripts/tests structure.
- Prefect pipeline folders.

### Backend pieces to replace or rename later

- Any endpoint copy that says "model" while returning manual scoring.
- Demand "model" naming in V2 docs/services must become baseline/scoring until real training exists.
- Room pressure "risk" can remain as risk, but not ML.
- Probable timetable generation must not be sold as learned placement.
- Optimized timetable variants must be described as optimization, not ML.

## Data audit

### Reusable data

- `backend/app/data/artists/artist_index.json`
- `backend/app/data/artists/enriched_artists.json`
- `backend/app/data/artists/manual_overrides.json`
- `backend/app/data/editions/*.json`
- `backend/app/data/timetables/historical_2022_2025.json`
- `backend/app/data/venue/fabrik_rooms.json`
- PostgreSQL tables created by V2 migrations.
- Evidence rows and artist metrics generated from V2 imports.

### Data debt

- Current predictive JSON files under `backend/app/data/predictions/` are not ML outputs.
- Some fields mix evidence, inference and prediction without a V3 model-run contract.
- 2026 event timing must be corrected in V3.1 as a continuous event.
- Saturation is currently a proxy/heuristic, not observed crowd measurement.
- Data lineage must be strengthened in V3.2-V3.8.

## Frontend audit

### Reusable frontend pieces

- Next.js + TypeScript app shell.
- Nexus/Fabrik cyberpunk visual identity.
- Dashboard component structure.
- Room/map/timetable UI ideas.
- Mobile-first styling foundations.
- Empty/error/loading panels.

### Frontend risks

- Any displayed "risk", "prediction", "probability" or "confidence" must later come from backend model outputs or documented evidence.
- No fake predictive constants should be added in V3.
- Frontend work should wait until V3.16, except metadata/docs if needed.
- UI should eventually show model confidence, drivers and limitations.

## Pipeline audit

### Reusable pipeline pieces

- `backend/app/pipelines/flows`
- `backend/app/pipelines/tasks`
- External ingestion flow structure.
- Social platform ingestion task structure.
- CLI scripts for local validation.

### Pipeline debt

- V3 needs reproducible dataset-building pipelines, not just ingestion scripts.
- Training, evaluation, model registry and prediction persistence are still missing.
- Prefect should orchestrate collectors, normalization, dataset building and retraining in later blocks.

## Documentation audit

### Reusable docs

- V2 setup and evidence docs.
- V2 Spotify/external ingestion/social platform docs.
- V2 historical timetable docs.
- V2 probable/optimized timetable docs.
- V2 frontend/map UX docs.
- Deployment docs.

### Documentation debt

- V2 docs that use "model" for weighted scoring must be reinterpreted as baseline/scoring.
- V3 docs must keep a hard separation between ML, baseline, scoring, heuristic, optimization and evidence.
- Future ML docs must include features, targets/proxies, metrics, limitations and reproducibility instructions.

## Reusable assets list

| Asset | Why it is reusable | Caveat |
| --- | --- | --- |
| Evidence layer | Provides source/confidence structure. | Needs V3 source/tool registry expansion. |
| Spotify cache | Useful popularity/profile feature source. | Must pass identity-confidence rules. |
| Historical timetables | Core source for placement and slot labels. | Needs audit/correction before labels. |
| Artist index | Canonical seed list. | Needs entity resolution expansion. |
| Genre layer | Useful categorical feature. | Not a predictive model. |
| Venue/room data | Needed for capacity and heatmap features. | Capacity confidence must be explicit. |
| Frontend shell | Good product base. | Must not render fake predictions. |
| Optimizer | Useful later for V3.14. | Not ML; must consume ML outputs later. |
| V2 scoring | Useful as baseline. | Must be renamed/reframed. |

## Pieces to replace or demote

| Piece | Current issue | V3 treatment |
| --- | --- | --- |
| V2 demand model | Weighted scoring, not trained ML. | Demote to baseline/scoring; train real model in V3.10. |
| Legacy prediction service | Deterministic prediction logic. | Keep as compatibility/baseline only. |
| Probable timetable service | Heuristic placement. | Replace with trained placement classifiers in V3.11. |
| Room risk service | Heuristic saturation approximation. | Replace with trained saturation/heatmap model in V3.12. |
| Optimized variants | Optimization over heuristic inputs. | Reuse only after ML outputs exist. |
| Predictive frontend constants | Can make UI look smarter than backend reality. | Remove/avoid in V3.16. |

## Predictive debt and rescue plan

### Debt 1 — Demand is not real ML yet

Current V2 demand logic should be treated as evidence-backed scoring. It may become:

- baseline model;
- feature engineering reference;
- explanation inspiration.

It must not be the final V3 demand model.

Rescue block:

```text
V3.10 — Modelo ML real de demanda y popularidad de artistas
```

### Debt 2 — Timetable placement is heuristic

Current probable timetable generation is useful as a prototype and baseline. It does not learn room/time probabilities from data.

Rescue block:

```text
V3.11 — Modelo ML real de colocación en sala y franja
```

### Debt 3 — Saturation is proxy/heuristic

Current room pressure helps the UI, but it is not trained from observed saturation data.

Rescue block:

```text
V3.12 — Modelo ML real de saturación y heatmap
```

### Debt 4 — Attendance prediction has high uncertainty

Attendance prediction must eventually use event-level features and communicate uncertainty.

Rescue block:

```text
V3.13 — Predicción ML de asistencia 2026 low/mid/high
```

### Debt 5 — Optimizer uses non-ML inputs

OR-Tools/optimization can stay, but it should optimize over ML outputs.

Rescue block:

```text
V3.14 — Optimización de horarios usando salidas ML
```

### Debt 6 — No model registry yet

Predictions cannot be fully audited without model runs, metrics and artifact metadata.

Rescue block:

```text
V3.15 — Model registry, APIs ML y panel de evaluación
```

## V3.0 closure decisions

The detailed closure decisions live in:

```text
docs/v3-0-closure-decisions.md
```

Required before commit:

- Record the exact V3 start commit.
- Confirm visual naming.
- Confirm that current V2 predictive services are not final ML.
- Confirm that no frontend runtime was touched in V3.0.

## V3.0 validation checklist

- [ ] Branch is `refactor/v3-ml-first`.
- [ ] `README_V3.md` exists and explains ML-first rules.
- [ ] `docs/v3-predictive-audit.md` exists and contains this classification.
- [ ] `docs/v3-0-closure-decisions.md` exists and has a real `V3_START_COMMIT`.
- [ ] Predictive endpoints are inventoried.
- [ ] Predictive services are inventoried.
- [ ] Reusable assets are documented.
- [ ] Replacement/demotion targets are documented.
- [ ] Naming conventions exist.
- [ ] `python backend/scripts/check_v3_predictive_audit.py` passes.
- [ ] `pytest` passes from `backend/`.
- [ ] Commit is made with `audit predictive core for ml first v3`.

## V3.0 educational note — baseline vs heuristic vs ML

A baseline can be simple and still legitimate if we label it honestly. A heuristic can also be useful if it captures domain knowledge. The problem is not using simple methods; the problem is calling them "ML" when they have not been trained and validated.

For V3, the clean sequence is:

```text
evidence/data -> features -> labels/proxies -> baseline -> trained ML -> metrics -> persisted predictions -> frontend
```

V3.0 only prepares the project for that sequence.
