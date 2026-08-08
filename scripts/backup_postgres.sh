#!/usr/bin/env bash
set -euo pipefail

: "${ZKSATO_DATABASE_URL:?Set ZKSATO_DATABASE_URL}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/zksato-${STAMP}.dump"
pg_dump --format=custom --no-owner --no-acl --dbname="$ZKSATO_DATABASE_URL" --file="$OUT"
sha256sum "$OUT" > "${OUT}.sha256"
echo "$OUT"
