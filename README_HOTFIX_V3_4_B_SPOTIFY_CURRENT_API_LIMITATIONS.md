# Hotfix V3.4-B — Spotify current API limitations

Este ZIP corrige la interpretación del probe real de Spotify.

## Qué cambia

- `backend/app/collectors/official_apis.py`
  - Persiste todas las métricas oficiales que Spotify devuelva realmente.
  - No inventa followers, popularity, genres, monthly listeners ni play counts.
  - Marca Spotify como `partial` cuando faltan métricas públicas esperadas.
  - Añade `unavailable_metric_keys` y `field_presence`.

- `backend/app/schemas/external_ingestion_v3.py`
  - Expone `unavailable_metric_keys`, `field_presence` y `official_api_limitation` en la respuesta del endpoint.

- `backend/app/services/v3_external_api_probe_service.py`
  - Rellena esos nuevos campos en cada resultado del probe.

- `backend/tests/test_api_v3_external_api_probes.py`
  - Mantiene el test offline de métricas completas si Spotify las devuelve.
  - Añade un test offline para el caso real actual: Spotify omite followers/popularity/genres.

- `docs/*`
  - Actualiza la documentación para no prometer métricas que la API oficial puede no devolver.

## Validación

Desde la raíz del proyecto:

```powershell
cd backend
pytest tests/test_api_v3_external_api_probes.py
pytest
```

Resultado esperado:

```text
7 passed
pytest global passed
```

Con backend levantado:

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

Resultado esperado del probe real:

- Si Spotify devuelve followers/popularity/genres, aparecerán en `metric_keys`.
- Si Spotify no los devuelve, aparecerán en `unavailable_metric_keys`.
- En ese segundo caso, `status` debe ser `partial` y `official_api_limitation` debe explicar la limitación.

## Commit sugerido

```text
handle spotify current api metric limitations
```
