# V3.4-B hotfix — Spotify full metrics and reused snapshots

## Problema

Spotify ya tenía el collector enriquecido para consultar el detalle oficial del artista y top tracks, pero en ejecución real podía reutilizar snapshots antiguos que solo habían normalizado:

- `spotify_artist_url`
- `spotify_image_url`
- `spotify_external_id`

Eso impedía cerrar V3.4-B porque el subroadmap exige persistir, cuando existan:

- `spotify_followers_total`
- `spotify_popularity_score`
- `spotify_genres`
- `spotify_artist_url`
- `spotify_image_url`
- `spotify_external_id`

## Corrección

El servicio de probes mantiene la deduplicación de raw snapshots, pero cuando un snapshot se reutiliza ahora inserta únicamente las métricas que faltan para ese snapshot. Así no se inflan duplicados y sí se permite que una mejora del normalizador complete métricas nuevas.

## Validación esperada
