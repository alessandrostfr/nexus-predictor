#!/usr/bin/env bash

# Backup PostgreSQL de Nexus Predictor en producción.
# Genera un dump comprimido de la base nexus_predictor.
# Debe ejecutarse en el VPS donde existe el contenedor nexus-postgres.

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

# Retención simple: eliminar backups PostgreSQL de Nexus con más de 14 días.
find "${BACKUP_DIR}" -name "nexus_postgres_*.sql.gz" -type f -mtime +14 -delete

echo "Backup created successfully:"
echo "${BACKUP_FILE}"
