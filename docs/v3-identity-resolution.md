# V3.3 — Identidad de artistas y entity resolution

## Objetivo

V3.3 crea una capa de identidad canónica antes de usar métricas externas como
features. El problema que resuelve es crítico para ML: si asociamos el perfil de
Spotify, SoundCloud, YouTube o una red social al artista incorrecto, el modelo
aprenderá datos falsos.

## Qué implementa este bloque

- `artist_master`: identidad canónica de cada artista.
- `artist_aliases`: variantes de nombre, aliases y nombres de actuaciones.
- `artist_identity_links`: enlaces revisados o pendientes hacia perfiles externos.
- `artist_identity_candidates`: candidatos que necesitan revisión manual.
- Normalización determinista de nombres.
- Matching inicial por slug, nombre, links y external_id cuando existen.
- Endpoints admin/debug para coverage, listado, detalle y revisión.
- UI mínima en `/admin/data-review` para revisar candidatos desde frontend.
- Script de validación `check_v3_identity_resolution.py`.

## Decisiones de alineación cerradas

```text
minimum confidence for features = verified/high
top artist manual review = required for external profiles
```

La identidad interna `nexus_seed` se marca como verificada porque procede del
cartel/dataset del proyecto. Pero cualquier perfil externo de artistas top o
2026 queda sujeto a revisión si no tiene confianza suficiente.

## Regla ML importante

Un link externo con confidence `medium`, `low`, `unknown`, `pending_review` o
`rejected` **no puede alimentar features ML**. Puede existir como evidencia o
candidato, pero no debe entrar en entrenamiento hasta que sea revisado.

## Endpoints

```text
POST /api/v3/identity/rebuild?reset=true
GET  /api/v3/identity/coverage
GET  /api/v3/identity/conventions
GET  /api/v3/identity/artists?limit=10
GET  /api/v3/identity/artists/{canonical_artist_key}
GET  /api/v3/identity/candidates?status=pending_review
POST /api/v3/identity/candidates/{candidate_id}/review
```

## Comandos de consola para endpoints

Con el backend arrancado en `127.0.0.1:8000`:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v3/identity/rebuild?reset=true"

curl.exe "http://127.0.0.1:8000/api/v3/identity/coverage"

curl.exe "http://127.0.0.1:8000/api/v3/identity/conventions"

curl.exe "http://127.0.0.1:8000/api/v3/identity/artists?limit=5"

curl.exe "http://127.0.0.1:8000/api/v3/identity/artists/angerfist"

curl.exe "http://127.0.0.1:8000/api/v3/identity/candidates?status=pending_review&limit=5"
```

Para revisar un candidato concreto, sustituye `<candidate_id>`:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v3/identity/candidates/<candidate_id>/review" `
  -H "Content-Type: application/json" `
  -d "{\"decision\":\"verified\",\"confidence\":\"high\",\"reviewed_by\":\"alessandro\",\"notes\":\"Perfil revisado manualmente.\"}"
```

Para rechazar:

```powershell
curl.exe -X POST "http://127.0.0.1:8000/api/v3/identity/candidates/<candidate_id>/review" `
  -H "Content-Type: application/json" `
  -d "{\"decision\":\"rejected\",\"reviewed_by\":\"alessandro\",\"notes\":\"No corresponde al artista correcto.\"}"
```

## Validación

Desde backend:

```powershell
alembic upgrade head
pytest tests/test_api_v3_identity_resolution.py
pytest
```

Desde la raíz del repo:

```powershell
python backend/scripts/check_v3_identity_resolution.py
```

Frontend opcional:

```powershell
cd frontend
npm run typecheck
npm run build
```

## Qué NO hace este bloque

- No hace scraping nuevo.
- No consume SoundCloud todavía.
- No entrena modelos.
- No genera features finales.
- No convierte el matching en ML.

## Concepto ML aprendido

**Entity resolution**: decidir cuándo dos registros de distintas fuentes
representan a la misma entidad real. En este proyecto significa decidir si un
perfil de Spotify/SoundCloud/YouTube/red social pertenece realmente al DJ del
cartel de Nexus.

## Estado tras el bloque

- V3.0 cerrado.
- V3.1 cerrado.
- V3.2 cerrado.
- V3.3 crea identidad canónica y revisión de perfiles.
- Siguiente bloque: V3.4 — Ingesta masiva híbrida y evaluación de herramientas.
