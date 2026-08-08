#!/usr/bin/env bash
set -euo pipefail

: "${ZKSATO_DATABASE_URL:?Set ZKSATO_DATABASE_URL}"
: "${1:?Usage: scripts/restore_postgres.sh BACKUP.dump}"
if [[ "${CONFIRM_RESTORE:-}" != "zksato" ]]; then
  echo "Refusing restore. Set CONFIRM_RESTORE=zksato after verifying the target database." >&2
  exit 2
fi
BACKUP="$1"
if [[ -f "${BACKUP}.sha256" ]]; then
  sha256sum -c "${BACKUP}.sha256"
fi
pg_restore --clean --if-exists --no-owner --no-acl --dbname="$ZKSATO_DATABASE_URL" "$BACKUP"
echo "Restore complete. Run migrations and reconciliation before enabling broker execution."
