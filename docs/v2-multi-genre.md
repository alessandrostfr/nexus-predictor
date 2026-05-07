# Nexus Predictor V2.5 — Subgéneros múltiples

Este bloque reemplaza la lectura de `primary_genre_seed` como verdad final por una capa V2 con:

- `main_genre`
- `secondary_genres`
- `genre_confidence`
- `genre_confidence_score`
- `genre_sources`
- filas persistidas en `artist_genres`
- evidencia en `evidence_items`
- métricas derivadas en `artist_metrics`

## Principios

La clasificación no oculta incertidumbre. Cuando el sistema solo puede inferir por contexto de lineup o por una pista débil, el artista queda con confianza baja y `needs_manual_review=true`.

## Fuentes usadas

- Overrides versionados de `genre_overrides.json`.
- `primary_genre_seed` de V1 como evidencia media, no como verdad absoluta.
- Géneros cacheados de Spotify cuando existen.
- Evidencias V2 con claves relacionadas con género, Beatport o 1001Tracklists.
- Metadata de perfiles de plataforma cuando contiene campos de género/estilo.
- Reglas de keywords.
- Hints curados V2 de baja/media confianza para reducir Unknown sin esconder revisión pendiente.
- Fallback contextual `Hard Dance` de baja confianza cuando no hay señal suficiente.

## Endpoints principales

```text
GET  /api/genres
GET  /api/genres/taxonomy
GET  /api/genres/artists
GET  /api/genres/artists/{slug}
GET  /api/genres/editions/{year}
GET  /api/genres/v2/coverage
GET  /api/genres/v2/comparison
POST /api/genres/v2/rebuild?reset=true
```

## Validación

```powershell
cd backend
alembic -c alembic.ini upgrade head
python scripts/check_v2_multi_genre.py
pytest tests/test_api_v2_multi_genre.py
pytest
```

## Commit

```text
support multi genre artist classification
```
