# Nexus Predictor V2 — Roadmap position

## Current status

Closed through:

- V2.0 — Foundations V2
- V2.1 — Evidence layer
- V2.2 — Spotify real
- V2.3 — External ingestion base
- V2.4 — Social/music platforms
- V2.5 — Multi-genre classification
- V2.6 — Historical timetables 2022-2025
- V2.7 — Demand and popularity model V2

## Active result after this block

V2.7 adds an evidence-backed demand model with:

- `popularity_score`
- `career_score`
- `momentum_score`
- `nexus_affinity_score`
- final `demand_score`
- explainable features and factors per artist
- fallback mode when external data is incomplete
- persisted prediction snapshots
- V1/V2 score comparison endpoints

## Next block

**V2.8 — Probable 2026 timetable**

Planned scope:

- use V2.7 demand scores and V2.6 historical slots
- learn room/time patterns by year, room, genre, headliner slot and demand
- generate a probable 2026 timetable
- mark confidence and reasons per slot
- distinguish prediction clearly from official timetable

## Methodology

- Follow the V2 roadmap strictly.
- Work one complete block per macropaso whenever reasonable.
- Deliver a ZIP with a `nexus-predictor/` root folder.
- Keep commits in English.
- Keep evidence/source/confidence traceability.
- Do not start frontend migration until V2.10.
- Do not start schedule optimization until V2.9.

## Commit for this block

`build v2 demand prediction model`

## Estimated progress after closing

62%
