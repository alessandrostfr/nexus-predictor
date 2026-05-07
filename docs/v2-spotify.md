# Nexus Predictor V2.2 — Spotify real

Este bloque activa Spotify Developer API con Client Credentials para enriquecer artistas Nexus con datos musicales públicos y trazables.

## Qué añade

- Variables `SPOTIFY_CLIENT_ID` y `SPOTIFY_CLIENT_SECRET`.
- Cliente Spotify con Client Credentials.
- Matching `artist_slug` Nexus → `spotify_artist_id`.
- Cache PostgreSQL en `spotify_artist_cache`.
- Guardado de avatar, popularity, followers, genres, top tracks, releases y embed URL.
- Evidencias atómicas en `evidence_items`.
- Métricas derivadas en `artist_metrics`.
- Perfil genérico en `platform_profiles`.
- Endpoints API seguros.
- Scripts de validación y refresh.

## Tabla nueva

`spotify_artist_cache` guarda el último snapshot Spotify por artista:

- `artist_slug`
- `spotify_artist_id`
- `spotify_url`
- `embed_url`
- `avatar_url`
- `popularity`
- `followers`
- `genres_json`
- `top_tracks_json`
- `releases_json`
- `match_confidence`
- `last_refreshed_at`

Las métricas importantes se duplican en la capa de evidencias para que el modelo V2 pueda explicar de dónde salen los scores.

## Variables de entorno

En `backend/.env`:

```env
SPOTIFY_CLIENT_ID=tu_client_id
SPOTIFY_CLIENT_SECRET=tu_client_secret
SPOTIFY_DEFAULT_MARKET=ES
```

Sin credenciales, la app no se rompe: `/api/spotify/status` informa `configured=false` y los refresh devuelven un error controlado.

## Validación

```powershell
cd backend
alembic -c alembic.ini upgrade head
python scripts/check_v2_spotify.py
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Endpoints:

```txt
GET  /api/spotify/status
GET  /api/spotify/artists/project-one
POST /api/spotify/artists/project-one/refresh?force=true
POST /api/spotify/refresh-top-artists?limit=5&force=false
GET  /api/evidence/artists/project-one
GET  /api/evidence/artists/project-one/metrics
```

## Refresh desde CLI

```powershell
python scripts/refresh_spotify_artist.py project-one --force
python scripts/refresh_spotify_artist.py angerfist --force
```

## Resultado esperado con credenciales

- El artista queda cacheado en `spotify_artist_cache`.
- Se crea/actualiza perfil `platform_profiles` con `platform=spotify`.
- Aparecen evidencias con claves `spotify.*`.
- Aparecen métricas `spotify_popularity`, `spotify_followers`, `spotify_top_track_count`, `spotify_release_count` y `spotify_genres`.

## Commit

```bash
git commit -m "integrate spotify artist enrichment pipeline"
```

## Progreso

Al cerrar este bloque, la V2 queda al 20%.
