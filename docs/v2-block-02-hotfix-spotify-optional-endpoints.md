# V2.2 hotfix - Spotify optional catalog endpoints

Spotify artist matching and profile enrichment must remain useful even when an
optional catalog endpoint returns `403 Forbidden`. This hotfix keeps the artist
refresh alive when `top-tracks` or `albums` is denied by Spotify for the current
app, market or quota mode.

## Behavior after the hotfix

- Artist search and artist profile data remain mandatory.
- Top tracks are stored when Spotify allows the endpoint.
- Releases are stored when Spotify allows the endpoint.
- If an optional endpoint is denied, the refresh still caches avatar,
  popularity, followers, genres, Spotify URL and embed URL.
- The response includes warnings so the missing data is transparent.
- No Spotify secret or token is exposed in API errors.

## Validation

```powershell
cd backend
python scripts/refresh_spotify_artist.py angerfist --force
python scripts/refresh_spotify_artist.py da-tweekaz --force
python scripts/refresh_spotify_artist.py project-one --force
pytest
```

A successful refresh may include warnings for top tracks/releases if Spotify
denies those endpoints. This is acceptable for V2.2 as long as artist profile
cache and evidence are created.
