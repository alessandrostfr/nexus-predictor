# Hotfix V3.4-B — Spotify test assertion

Este hotfix corrige solo el test `backend/tests/test_api_v3_external_api_probes.py`.

## Problema

El código devuelve correctamente:

`Exact Spotify track play counts and monthly listeners are not exposed by the official Web API.`

Pero el test buscaba literalmente:

`not exact plays`

La idea del test era correcta, pero la cadena era demasiado rígida.

## Aplicación recomendada

Desde la raíz del repo:

```powershell
git apply .\patches\spotify_test_assertion.patch
```

Después valida:

```powershell
cd backend
pytest tests/test_api_v3_external_api_probes.py
pytest
```

Resultado esperado:

```text
6 passed
pytest global passed
```
