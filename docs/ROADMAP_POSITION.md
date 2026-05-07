# Nexus Predictor roadmap position

## Current roadmap

- V1 MVP: closed.
- V2.0 Foundations: closed.
- V2.1 Evidence layer: closed.
- V2.2 Spotify real: closed.
- V2.3 External ingestion base: closed.
- V2.4 Social networks and music platforms: delivered in this block, pending local validation.

## Current block

**V2.4 — Redes sociales y plataformas musicales ampliadas**

Scope:

- Mixed JSON/CSV ingestion for social metrics.
- Candidate/official social profile registry.
- Music-platform profiles for Last.fm, SoundCloud, Apple Music, Beatport and 1001Tracklists.
- Optional Last.fm API refresh for top tracks.
- Evidence-backed `social_reach_score`, `engagement_score` and `momentum_score`.
- Coverage and freshness API.

## Next block

**V2.5 — Subgéneros múltiples y reducción de Unknown**

Planned scope:

- Replace the single V1 genre seed with `main_genre`, `secondary_genres`, confidence and evidence.
- Use Spotify genres, platform evidence, Beatport/1001Tracklists signals, bios, labels and keyword rules.
- Reduce Unknown artists without hiding uncertainty.
