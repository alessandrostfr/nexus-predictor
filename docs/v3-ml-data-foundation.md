# V3.2 — Arquitectura de datos ML-ready

Este bloque crea la capa mínima para que Nexus Predictor V3 pueda entrenar modelos reales más adelante sin depender de scripts sueltos ni valores inventados.

## Qué problema resuelve

En V2 ya existían evidencias, métricas y predicciones heurísticas, pero todavía no existía una separación completa entre:

- dato crudo capturado;
- dato normalizado;
- dataset versionado;
- feature vector;
- label o proxy;
- ejecución de modelo;
- predicción persistida.

V3.2 crea esa separación. Todavía no entrena modelos. Prepara la base reproducible para que V3.7, V3.8, V3.9 y V3.10 puedan construir datasets, features, baselines y ML real.

## Decisiones cerradas

### raw_payload

`raw_payload` se guarda como `JSONB` en PostgreSQL siempre que sea viable.

Motivo: V3 necesita auditar, reprocesar y normalizar snapshots sin perder estructura. `JSONB` permite conservar payloads de APIs, herramientas externas, scrapers o CSV/manual review con buena capacidad de consulta posterior.

### Retención de snapshots pesados

Política inicial: **sin borrado automático en V3.2**.

Los snapshots pesados se conservarán mientras el proyecto esté en fase de investigación/ML. Más adelante, cuando tengamos fuentes reales voluminosas, podremos añadir una política de retención por `source_type`, `entity_type`, tamaño y valor ML. De momento borrar demasiado pronto sería peor que almacenar de más, porque rompería reproducibilidad.

## Tablas creadas

| Tabla | Responsabilidad | Usa payload JSONB | Fase futura |
|---|---|---:|---|
| `raw_sources` | Registro de fuentes para ingesta ML | Sí | V3.4 |
| `raw_snapshots` | Payloads crudos capturados | Sí | V3.4/V3.5/V3.6 |
| `normalized_metrics` | Métricas normalizadas por entidad/fuente | Sí | V3.8 |
| `ml_datasets` | Manifest de datasets versionados | Sí | V3.7/V3.8/V3.9 |
| `ml_feature_snapshots` | Vectores de features por entidad | Sí | V3.8 |
| `ml_labels` | Targets/proxies versionados | Sí | V3.7 |
| `ml_model_runs` | Entrenamientos, métricas y artefactos | Sí | V3.9/V3.10+ |
| `ml_predictions` | Outputs persistidos de modelos | Sí | V3.10+ |

## Convenciones iniciales

### source_type

Valores iniciales:

```text
spotify, soundcloud, youtube, lastfm, musicbrainz, social, events, venue, manual, internal, web
```

### confidence

Valores iniciales:

```text
verified, high, medium, low, rejected, unknown
```

### extraction_method

Valores iniciales:

```text
api, official_api, open_source_tool, httpx_bs4, playwright, manual_review, csv_import, internal_seed, unknown
```

### label_type

Valores iniciales:

```text
confirmed, inferred, proxy, manual_evidence, rejected
```

Un proxy no es una verdad directa. Puede entrenar un modelo solo si queda documentado como proxy.

## Endpoints de inspección

```text
GET /api/v3/ml-data/coverage
GET /api/v3/ml-data/contracts
GET /api/v3/ml-data/conventions
```

Estos endpoints son de debug/desarrollo. No devuelven raw payloads ni secretos.

## Qué NO hace este bloque

- No hace scraping real.
- No entrena modelos.
- No crea labels reales.
- No crea features definitivas.
- No cambia el frontend.
- No convierte heurísticas V2 en ML.

## Concepto ML aprendido

**Reproducibilidad en ML**: poder reconstruir el dataset, saber qué datos entraron, qué features se generaron, qué labels se usaron, qué modelo se entrenó y qué predicciones salieron.

Sin esta capa, un modelo puede parecer que funciona, pero no sería defendible.

## Validación

Desde backend:

```powershell
alembic upgrade head
pytest tests/test_api_v3_ml_data_foundation.py
pytest
```

Desde raíz del repo:

```powershell
python backend/scripts/check_v3_ml_data_foundation.py
```

## Estado tras el bloque

- V3.0 cerrado.
- V3.1 cerrado.
- V3.2 crea la base ML-ready.
- Siguiente bloque: V3.3 — Identidad de artistas y entity resolution.
