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

## Active result after this block

V2.6 adds a persisted historical timetable layer with:

- normalized 2022, 2023, 2024 and 2025 timetable slots
- Friday/Saturday split for 2024 and 2025
- canonical Fabrik rooms and historical aliases
- verified 2025 correction to seven real rooms
- start/end times and duration fields
- headliner, warm-up, closing and special-show flags
- source, confidence, extraction method and review status
- integrity checks for overlaps and incomplete slots

## Next block

**V2.7 — Demand and popularity model V2**

Planned scope:

- advanced features from evidence, Spotify, social/platform metrics, career events, genres and historical timetable slots
- separate popularity, career, momentum, Nexus affinity and demand scores
- explainable factors per artist
- fallback mode when data is incomplete

## Methodology

- Follow the V2 roadmap strictly.
- Work one complete block per macropaso whenever reasonable.
- Deliver a ZIP with a `nexus-predictor/` root folder.
- Keep commits in English.
- Keep evidence/source/confidence traceability.
- Do not start frontend migration until V2.10.
- Do not start timetable prediction until V2.8.
- Do not start schedule optimization until V2.9.

## Commit for this block

`structure historical timetable dataset`

## Estimated progress after closing

52%
