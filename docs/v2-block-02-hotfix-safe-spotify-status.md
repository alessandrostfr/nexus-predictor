# V2.2 hotfix - safe Spotify status message

This hotfix keeps the V2.2 Spotify integration behaviour unchanged, but removes explicit secret-variable wording from public API responses.

## Why

`GET /api/spotify/status` must confirm whether Spotify is configured without leaking secret names or values in the serialized response body.

## Validation

```powershell
cd backend
pytest tests/test_api_v2_spotify.py
pytest
```
