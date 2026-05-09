# V3.4-B hotfix — Spotify current API limitations

## Problem

The V3.4-B collector was already enriched to call the official Spotify artist
detail endpoint and top-tracks endpoint. Offline tests passed, but a real probe
could still return only:

- `spotify_artist_url`
- `spotify_image_url`
- `spotify_external_id`

This is not necessarily a code failure. Spotify's current Web API can omit or
deprecate public fields that older versions exposed, especially artist followers,
artist popularity and track popularity. Exact track play counts and monthly
listeners are not exposed by the official Web API.

## Fix

The Spotify collector now stays technically honest:

- persists every metric actually returned by the official API;
- never invents followers, popularity, genres, monthly listeners or play counts;
- marks the probe as `partial` when expected public metrics are absent;
- exposes `unavailable_metric_keys` and `field_presence` in the probe response;
- stores the absence as a limitation in the raw snapshot/hint payload.

## Expected real validation

A current real probe may legitimately return only URL/image/external-id plus
optional top-track metadata. In that case the response should show:

- `status`: `partial`
- `unavailable_metric_keys`: includes missing Spotify metrics such as
  `spotify_followers_total` or `spotify_popularity_score`
- `official_api_limitation`: explains that absent values were not invented

## PowerShell validation

```powershell
cd backend
pytest tests/test_api_v3_external_api_probes.py
pytest
```

With backend running:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/v3/external-ingestion/official-probes" `
  -ContentType "application/json" `
  -Body '{
    "limit": 1,
    "sources": ["spotify_web_api"],
    "execute_real_calls": true,
    "persist": true
  }' | ConvertTo-Json -Depth 30
```

## Result interpretation

If Spotify returns followers/popularity/genres, they must appear in `metric_keys`.
If Spotify does not return them, they must appear in `unavailable_metric_keys`.
Both outcomes are valid; silently pretending the metrics exist is not valid.
