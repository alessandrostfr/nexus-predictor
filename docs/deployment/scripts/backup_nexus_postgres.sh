#!/usr/bin/env bash

# Backup PostgreSQL for Nexus Predictor production.
# Generates a compressed dump of the nexus_predictor database.
# Must run on the VPS where the nexus-postgres container exists.

set -Eeuo pipefail
umask 077

BACKUP_DIR="/opt/alessandro/backups/nexus-postgres"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="${BACKUP_DIR}/nexus_postgres_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "Creating Nexus PostgreSQL backup..."
echo "Target: ${BACKUP_FILE}"

docker exec nexus-postgres pg_dump \
  -U nexus_user \
  -d nexus_predictor \
  | gzip > "${BACKUP_FILE}"

gzip -t "${BACKUP_FILE}"
chmod 600 "${BACKUP_FILE}"
chown alessandro:alessandro "${BACKUP_FILE}"

# Simple retention: remove Nexus PostgreSQL backups older than 14 days.
find "${BACKUP_DIR}" -name "nexus_postgres_*.sql.gz" -type f -mtime +14 -delete

echo "Backup created successfully:"
echo "${BACKUP_FILE}"
