#!/usr/bin/env bash
set -euo pipefail

# Provisioning script for zksato user & database on zpostgresql and zredis
# Usage: ./scripts/provision_zksato_infra.sh

POSTGRES_HOST="${POSTGRES_HOST:-zpostgresql}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_ADMIN_USER="${POSTGRES_ADMIN_USER:-postgres}"
POSTGRES_DB_NAME="${POSTGRES_DB_NAME:-zksato}"
ZKSATO_DB_USER="${ZKSATO_DB_USER:-zksato}"
ZKSATO_DB_PASSWORD="${ZKSATO_DB_PASSWORD:-zksato_dev_only}"

REDIS_HOST="${REDIS_HOST:-zredis}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_USER="${REDIS_USER:-zksato}"
REDIS_PASSWORD="${REDIS_PASSWORD:-zksato_redis_pass}"

echo "=== 1. Provisioning PostgreSQL user and database (${POSTGRES_HOST}:${POSTGRES_PORT}) ==="

SQL_COMMANDS="
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${ZKSATO_DB_USER}') THEN
    CREATE ROLE ${ZKSATO_DB_USER} LOGIN PASSWORD '${ZKSATO_DB_PASSWORD}';
  END IF;
END
\$\$;

SELECT 'CREATE DATABASE ${POSTGRES_DB_NAME} OWNER ${ZKSATO_DB_USER};'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${POSTGRES_DB_NAME}')\gexec

GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB_NAME} TO ${ZKSATO_DB_USER};
"

if command -v psql &> /dev/null; then
  echo "Executing PostgreSQL provisioning via psql..."
  # If connecting via network or container
  PGPASSWORD="${POSTGRES_ADMIN_PASSWORD:-}" psql -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_ADMIN_USER}" -c "$SQL_COMMANDS" || echo "Note: direct psql execution skipped or failed; ensure database and user are provisioned in docker-compose."
else
  echo "psql client not found on host. Ensure PostgreSQL container initializes zksato user and database via environment variables."
fi

echo "=== 2. Redis ACL configuration (${REDIS_HOST}:${REDIS_PORT}) ==="
echo "Redis User: ${REDIS_USER}"
echo "Redis ACL string suggestion for redis.conf / ACL file:"
echo "user ${REDIS_USER} on >${REDIS_PASSWORD} ~* +@all"

echo "=== Provisioning check complete ==="
