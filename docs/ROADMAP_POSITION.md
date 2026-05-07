# Nexus Predictor V2 - Roadmap position

## Closed V2 blocks

- V2.0 - Foundations V2: PostgreSQL, Docker Compose, Alembic, settings and pipeline structure.
- V2.1 - Evidence layer: sources, evidence, metrics, profiles, events and venue prestige.
- V2.2 - Spotify real: artist cache, profile fields, popularity, releases and safe optional top-track handling.
- V2.3 - External ingestion base: Prefect flow and external career/venue signals.
- V2.4 - Social networks and music platforms: mixed JSON/CSV metrics and Last.fm top tracks.
- V2.5 - Multi-genre classification: main genre, secondary genres, confidence and traceability.
- V2.6 - Historical timetables 2022-2025: normalized slots and verified 2025 seven-room correction.
- V2.7 - Demand and popularity model: evidence-backed score components and explanations.

## Current block

**V2.8 — Predicción de horario probable 2026**

Delivered scope:

- Probable room/day/time assignment for the 2026 lineup.
- Historical pattern learning from V2.6.
- Demand-aware slot assignment from V2.7.
- Confidence, probability and reasons per slot.
- Explicit API contract that the timetable is predicted, not official.
- Integrity checks for impossible overlaps, duplicate artists and invalid rooms.

## Next block

**V2.9 — Generador de horario óptimo con 3 variantes**

Planned scope:

- Generate three optimized timetables: anti-crowding, balanced and fan experience.
- Define constraints for rooms, capacities, genres, top artists and overlaps.
- Use OR-Tools if it fits the final constraint model.
- Expose comparable `crowding_score`, `conflict_score` and `experience_score`.
- Keep V2.8 probable timetable separate from V2.9 optimized alternatives.

## Commit

`predict probable 2026 timetable`

## Estimated progress after closing

70% of Nexus Predictor V2.
