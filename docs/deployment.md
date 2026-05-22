# Deployment plan — Nexus Predictor

Este documento define el plan de despliegue profesional de Nexus Predictor dentro de la infraestructura VPS del portfolio.

## Estado

Deployment pendiente. El proyecto está preparado para despliegue futuro, pero primero se consolidarán:

- documentación profesional;
- capturas;
- dominio/subdominio;
- reverse proxy común del VPS;
- variables de entorno de producción;
- backups.

## Infraestructura objetivo

Proveedor previsto para el portfolio completo:

```text
IONOS VPS L+
Ubuntu LTS
Docker + Docker Compose
Reverse proxy
HTTPS con Let's Encrypt
PostgreSQL persistente
Backups automáticos
```

Subdominios propuestos:

```text
nexus.alessandrostfr.com      -> frontend Next.js
api-nexus.alessandrostfr.com  -> backend FastAPI
```

## Arquitectura de producción

```text
Internet
   │
   ▼
Reverse proxy HTTPS
   ├── nexus.alessandrostfr.com      -> frontend Next.js
   └── api-nexus.alessandrostfr.com  -> backend FastAPI
                                            │
                                            ▼
                                      PostgreSQL
```

## Variables de entorno

Backend:

```env
APP_NAME=Nexus Predictor
APP_VERSION=production
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@postgres:5432/nexus_predictor
BACKEND_CORS_ORIGINS=https://nexus.alessandrostfr.com
AUTO_CREATE_DATABASE_SCHEMA=false
AUTO_SEED_DATABASE=true
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
LASTFM_API_KEY=
YOUTUBE_API_KEY=
SOUNDCLOUD_CLIENT_ID=
SOUNDCLOUD_CLIENT_SECRET=
MUSICBRAINZ_USER_AGENT=NexusPredictorV3/0.1 (portfolio demo; contact: contacto@alessandrostfr.com)
ENABLE_YTDLP_METADATA_COLLECTOR=false
EXTERNAL_TIMEOUT_SECONDS=12
```

Frontend:

```env
NEXT_PUBLIC_API_BASE_URL=https://api-nexus.alessandrostfr.com/api
```

## Reglas de seguridad

- No subir archivos `.env`.
- No activar collectors externos sin rate limits y caché.
- No guardar secretos en logs.
- No presentar horarios o predicciones como datos oficiales.
- Mantener datos de demo si el proyecto se enseña públicamente.
- Probar restauración de backup antes de considerar el deploy estable.

## Validación post-deploy

Backend:

```powershell
Invoke-RestMethod https://api-nexus.alessandrostfr.com/api/health | ConvertTo-Json -Depth 30
```

Frontend:

```text
https://nexus.alessandrostfr.com
```

Checklist:

- frontend carga sin errores 500;
- backend responde healthcheck;
- CORS permite llamadas desde el dominio frontend;
- PostgreSQL persiste datos tras reinicio;
- certificados HTTPS activos;
- no hay secretos en logs;
- dashboard deja claro que las predicciones no son oficiales.

## Roadmap de despliegue

1. Preparar servidor base.
2. Configurar reverse proxy y HTTPS.
3. Crear red Docker común.
4. Desplegar PostgreSQL.
5. Desplegar backend.
6. Ejecutar migraciones.
7. Desplegar frontend.
8. Configurar backups.
9. Crear capturas reales desde la demo.
10. Enlazar demo desde portfolio y GitHub.
