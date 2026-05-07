# Nexus Predictor V2 - Roadmap position

## Closed V2 blocks

- V2.0 - Foundations V2: PostgreSQL, Docker Compose, Alembic, settings and pipeline structure.
- V2.1 - Evidence layer: source registry, evidence items, metrics, career events and venue prestige.

## Current block

V2.2 - Spotify real.

## Current block scope

- Configure `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET`.
- Use Spotify Client Credentials for public catalog data.
- Match Nexus artists to Spotify artist IDs.
- Store avatar, popularity, followers, genres, top tracks, releases and embed URLs.
- Cache Spotify payloads in PostgreSQL.
- Store Spotify values as V2 evidence and derived metrics.
- Fail safely when credentials are missing.

## Explicitly not included

- Instagram, TikTok, YouTube, SoundCloud, Apple Music, Beatport or 1001Tracklists.
- Multi-genre replacement.
- Historical timetable extraction.
- Next.js frontend migration.

Those belong to later V2 blocks.

## Commit

`integrate spotify artist enrichment pipeline`

## Estimated progress after closing

20%
