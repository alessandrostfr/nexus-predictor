# V3.4 external ingestion — operational notes

V3.4 is the data factory for future ML blocks. It does not train models and does not replace V2 predictions yet.

## Current macropaso

**V3.4-A — Arquitectura, contratos, seguridad, idempotencia y registros**

This macropaso creates:

- collector contracts;
- source registry;
- source capability matrix;
- tool evaluation registry;
- run and run-item tables;
- dry-run endpoint;
- secret policy;
- extraction policy;
- idempotency helpers;
- UTC/source timestamp fields;
- minimum coverage indexes.

## API endpoints introduced in V3.4-A

- `GET /api/v3/external-ingestion/architecture`
- `GET /api/v3/external-ingestion/sources`
- `GET /api/v3/external-ingestion/tools`
- `POST /api/v3/external-ingestion/dry-run`

These endpoints are offline and safe: they do not call external APIs.

## PowerShell validation examples

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v3/external-ingestion/architecture" | ConvertTo-Json -Depth 30
Invoke-RestMethod "http://127.0.0.1:8000/api/v3/external-ingestion/sources" | ConvertTo-Json -Depth 30
Invoke-RestMethod "http://127.0.0.1:8000/api/v3/external-ingestion/tools" | ConvertTo-Json -Depth 30
Invoke-RestMethod "http://127.0.0.1:8000/api/v3/external-ingestion/dry-run" -Method POST -ContentType "application/json" -Body '{"limit":5,"sources":["spotify_web_api","youtube_data_api"]}' | ConvertTo-Json -Depth 30
```

## Expected result

- Architecture returns `ready: true`.
- Sources return configured/not_configured states without secret values.
- Tools include yt-dlp, NewPipeExtractor and Playwright decisions.
- Dry-run returns `would_persist_raw_snapshots: false` and `would_persist_normalized_metrics: false`.
