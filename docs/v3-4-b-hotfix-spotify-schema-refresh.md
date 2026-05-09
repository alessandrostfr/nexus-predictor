# V3.4-B hotfix — Spotify full metrics schema refresh

This hotfix closes the Spotify full-metrics validation gap detected after the
first official API probe runs.

## Problem

Early Spotify snapshots for `adrenalize` were stored with only:

- `spotify_artist_url`
- `spotify_image_url`
- `spotify_external_id`

After the collector was improved, the endpoint could still reuse the old raw
snapshot and keep returning the old metric set.

## Fix

- Adds `SPOTIFY_FULL_METRICS_SCHEMA_REVISION = "v3.4-b-spotify-full-metrics-v2"`.
- Stores that schema revision in the Spotify raw payload.
- This changes the snapshot hash/key for the enriched Spotify payload, so the
  next probe creates a new traceable snapshot instead of reusing the old one.
- Keeps idempotency by still skipping metric keys that already exist for the
  same snapshot.
- Stores collector/normalizer version from the schema revision when available.

## Expected validation

A real Spotify probe with `limit=1` must include every metric currently returned by Spotify. URL/image/external-id should normally appear. Followers, artist popularity, genres and top-track popularity may be absent in the current API; when absent, they must be listed in `unavailable_metric_keys` and must not be invented.