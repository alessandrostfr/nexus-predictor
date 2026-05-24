# Nexus Predictor — VPS deployment runbook

## Production services

Repository path on VPS:

```bash
/opt/alessandro/apps/nexus-predictor
```

Branch used for this deployment block:

```bash
deploy/block-16-nexus-vps
```

Docker services:

- `nexus-web` — Next.js frontend.
- `nexus-api` — FastAPI backend.
- `nexus-postgres` — PostgreSQL production database.

Domains planned in Nginx Proxy Manager:

- `https://nexus.alessandrostfr.com` -> `nexus-web:3000`
- `https://api-nexus.alessandrostfr.com` -> `nexus-api:8020`

## Production commands

```bash
cd /opt/alessandro/apps/nexus-predictor

docker compose --env-file .env.production -f docker-compose.production.yml ps
docker compose --env-file .env.production -f docker-compose.production.yml logs api --tail 80
docker compose --env-file .env.production -f docker-compose.production.yml logs web --tail 80
docker compose --env-file .env.production -f docker-compose.production.yml logs postgres --tail 80
```

## Initial database setup

Run before starting API/web for the first time:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml up -d postgres
docker compose --env-file .env.production -f docker-compose.production.yml run --rm api alembic -c alembic.ini upgrade head
```

Then start the app:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml up -d api web
```

The API startup seeds the internal Nexus dataset used by the current product screens. Optional refreshes for Spotify/Last.fm must remain disabled unless credentials are configured intentionally.

## Health checks

```bash
curl -sS https://api-nexus.alessandrostfr.com/api/health
curl -I https://nexus.alessandrostfr.com
```

Internal Docker checks:

```bash
docker run --rm --network proxy curlimages/curl:8.10.1 -sS -i http://nexus-api:8020/api/health
docker run --rm --network proxy curlimages/curl:8.10.1 -I http://nexus-web:3000
```

## Backups

Backup script:

```bash
/opt/alessandro/scripts/backup_nexus_postgres.sh
```

Backup directory:

```bash
/opt/alessandro/backups/nexus-postgres
```

Suggested cron:

```cron
55 3 * * * /opt/alessandro/scripts/backup_nexus_postgres.sh >> /opt/alessandro/backups/nexus-postgres/backup_nexus_postgres.log 2>&1
```

Validate latest backup:

```bash
LATEST_NEXUS_BACKUP="$(ls -t /opt/alessandro/backups/nexus-postgres/nexus_postgres_*.sql.gz | head -n 1)"
echo "$LATEST_NEXUS_BACKUP"
gzip -t "$LATEST_NEXUS_BACKUP"
zcat "$LATEST_NEXUS_BACKUP" | head -n 20
```

## Notes

This deployment exposes the current ML-first work-in-progress state. Public communication should describe it honestly as an evolving data/ML product, not as a finished prediction engine.
