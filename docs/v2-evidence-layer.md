# Nexus Predictor V2.1 — Capa de evidencias

Este bloque crea la base de datos que permitirá explicar por qué un artista sube o baja en los modelos V2. La idea principal es que ningún dato relevante quede como una cifra opaca: cada métrica debe poder rastrearse hasta una fuente, URL, fecha de captura, confianza, método de extracción y notas.

## Tablas nuevas

- `sources`: registro estable de fuentes internas, públicas, oficiales, manuales o futuras APIs.
- `evidence_items`: evidencia atómica por artista y métrica.
- `artist_metrics`: métricas agregadas derivadas de evidencia, preparadas para features del modelo.
- `platform_profiles`: perfiles en plataformas musicales o de eventos como Spotify, Beatport, Resident Advisor o 1001Tracklists.
- `social_profiles`: perfiles y métricas sociales como Instagram, TikTok, YouTube, Facebook o X/Twitter.
- `career_events`: señales de carrera: eventos, festivales, roles, venues, headliner, país y año.
- `venue_prestige`: registro inicial de prestigio de salas, festivales y venues.

## Modelo de confianza

La V2 usa cuatro niveles de confianza:

- `low`: dato débil, pendiente o inferido con poca seguridad.
- `medium`: dato razonable pero todavía no verificado por una fuente fuerte.
- `high`: dato fiable por fuente interna/externa sólida.
- `verified`: dato confirmado oficialmente o por evidencia manual directa del usuario.

## Estados de evidencia

- `official`: fuente oficial.
- `confirmed`: dato confirmado por fuente aceptable.
- `estimated`: estimación explícita.
- `inferred`: inferencia transparente.
- `pending_review`: dato pendiente de revisión manual.

## Importador V1 → V2

El script `backend/scripts/seed_v2_evidence.py` importa el dataset V1 a la nueva capa V2:

```powershell
cd backend
python scripts/seed_v2_evidence.py --reset
```

El importador crea fuentes internas, evidencia base por artista, métricas iniciales y señales de carrera desde apariciones Nexus. También genera una primera capa de `venue_prestige` desde los datos de salas de Fabrik.

## Endpoints nuevos

- `GET /api/evidence/coverage`
- `POST /api/evidence/import-v1?reset=false`
- `GET /api/evidence/sources`
- `GET /api/evidence/artists/{artist_slug}`
- `GET /api/evidence/artists/{artist_slug}/metrics`
- `GET /api/evidence/venue-prestige`
- `POST /api/evidence/manual`

Ejemplo para registrar evidencia manual:

```json
{
  "artist_slug": "project-one",
  "metric_key": "manual.2025_room_correction",
  "metric_value": "La edición 2025 debe modelarse con 7 salas reales, no 13 escenarios.",
  "confidence": "verified",
  "status": "confirmed",
  "notes": "Evidencia manual del usuario basada en asistencia directa e imágenes de horarios."
}
```

## Validación del bloque

```powershell
cd backend
alembic -c alembic.ini upgrade head
python scripts/seed_v2_evidence.py --reset
python scripts/check_v2_evidence_layer.py
pytest
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## Resultado esperado

- Seeds V1 importados a PostgreSQL.
- Cada artista tiene evidencia base.
- La API permite consultar evidencia por artista.
- Hay fuente, URL cuando exista, fecha, confianza, método de extracción y notas.
- Los tests de integridad del bloque pasan.
