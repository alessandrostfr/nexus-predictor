# Roadmap position — Nexus Predictor V3

Current main roadmap block: **V3.4 — Ingesta masiva híbrida y evaluación de herramientas**.

Current operative subroadmap: **V3.4-B — Configuración, credenciales y probes oficiales**.

## Important navigation rule

V3.4 has its own approved **Subroadmap operativo V3.4**. Treat it as a temporary branch inside the main V3 roadmap:

```text
V3 roadmap
└── V3.4 — Ingesta masiva híbrida y evaluación de herramientas
    ├── V3.4-A — Arquitectura, contratos, seguridad, idempotencia y registros ✅ closed
    ├── V3.4-B — Configuración, credenciales y probes oficiales ← current
    ├── V3.4-C — yt-dlp, scraping controlado y evaluación open-source
    ├── V3.4-D — Normalización, calidad, readiness, fallback manual y contratos de métricas
    ├── V3.4-E — Run real de ingesta para todos los artistas Nexus 2026
    └── V3.4-F — Prefect, admin review, checks finales y cierre del bloque
```

When V3.4-F is closed, return to the main V3 roadmap at **V3.5 — SoundCloud-first artist intelligence**.

## Closed V3 blocks

- **V3.0** closed: critical predictive audit and ML-first branch guardrails.
- **V3.1** closed: real Nexus 2026 continuous event contract.
- **V3.2** closed: ML-ready data foundation.
- **V3.3** closed: canonical artist identity and entity resolution.
- **V3.4-A** closed: external collector architecture, contracts, security, idempotency and registries.

## Current V3.4-B objective

Configure and probe official APIs honestly:

- check Spotify, Last.fm, MusicBrainz, YouTube and SoundCloud credential readiness without exposing secret values;
- keep pytest offline and deterministic;
- allow controlled real probes only through explicit scripts/endpoints;
- persist raw snapshots and normalized metric candidates only when `execute_real_calls=true` and `persist=true`;
- register missing YouTube/SoundCloud credentials as `not_configured` or `access_unconfirmed`, never silently ignored;
- keep MusicBrainz conservative because it is identity metadata, not primary demand.

## Current source of truth

Use both documents together:

1. `nexus_predictor_v3_roadmap.pdf` for the main V3 direction and success criteria.
2. `nexus_predictor_v3_4_subroadmap_operativo_final.pdf` for the detailed V3.4-A → V3.4-F execution path.

## Current progress

- Main V3 progress after V3.4-A: **23.5%**.
- V3.4-B target progress after validation/commit: **25%**.
- V3.4 full target after V3.4-F: **32%**.

## Commit for this macropaso

```bash
git add .
git commit -m "probe official artist data apis"
```

## Methodology reminder

For each macropaso:

- review the updated repository first;
- reread the active roadmap/subroadmap block before coding;
- deliver complete files in a ZIP with root folder `nexus-predictor/`;
- keep code commented;
- avoid fake ML and fake frontend data;
- include specific validations;
- include PowerShell endpoint checks with `ConvertTo-Json -Depth 30`;
- include expected results;
- suggest commit in English;
- report block and project percentages.
