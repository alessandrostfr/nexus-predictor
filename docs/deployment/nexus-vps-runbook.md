# Nexus Predictor — VPS Production Runbook

## Current production state

Nexus Predictor is deployed as a full-stack application on the IONOS VPS.

Production URLs:

- Frontend: https://nexus.alessandrostfr.com
- API: https://api-nexus.alessandrostfr.com
- API health: https://api-nexus.alessandrostfr.com/api/health

Production path on VPS:

/opt/alessandro/apps/nexus-predictor

Production Git branch:

deploy/block-16-nexus-vps

Current Docker services:

- nexus-postgres
- nexus-api
- nexus-web

Docker Compose file:

docker-compose.production.yml

Environment file on VPS:

.env.production

Important: .env.production must never be committed.

---

## Production architecture

Nexus uses:

- Next.js frontend served by nexus-web.
- FastAPI backend served by nexus-api.
- PostgreSQL database served by nexus-postgres.
- Nginx Proxy Manager as reverse proxy.
- HTTPS certificates managed from Nginx Proxy Manager.
- Uptime Kuma for monitoring.
- Daily PostgreSQL backup through cron.

Network model:

- nexus-postgres only uses the internal Docker network.
- nexus-api uses the internal network and the shared proxy network.
- nexus-web uses the internal network and the shared proxy network.
- Only nexus-api and nexus-web are reachable by Nginx Proxy Manager.

---

## Nginx Proxy Manager routes

API proxy host:

- Domain: api-nexus.alessandrostfr.com
- Scheme: http
- Forward Hostname/IP: nexus-api
- Forward Port: 8020
- SSL: enabled
- Force SSL: enabled
- HTTP/2: enabled

Frontend proxy host:

- Domain: nexus.alessandrostfr.com
- Scheme: http
- Forward Hostname/IP: nexus-web
- Forward Port: 3000
- SSL: enabled
- Force SSL: enabled
- HTTP/2: enabled
- Websockets: enabled

---

## Standard production validation

Run from the VPS:

```bash
cd /opt/alessandro/apps/nexus-predictor

docker compose --env-file .env.production -f docker-compose.production.yml ps

curl -I https://nexus.alessandrostfr.com
curl -sS https://api-nexus.alessandrostfr.com/api/health