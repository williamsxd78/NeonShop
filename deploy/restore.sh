#!/usr/bin/env bash
# Restore a database backup (replaces current data). Usage: sudo ./deploy/restore.sh backups/db-XXXX.archive.gz
set -euo pipefail
cd "$(dirname "$0")"
[ -f "${1:-}" ] || { echo "Usage: sudo ./deploy/restore.sh backups/db-XXXX.archive.gz"; exit 1; }
set -a; . ./.env; set +a
read -rp "This REPLACES the current database '$DB_NAME'. Continue? [y/N]: " OK
[[ "$OK" =~ ^[Yy]$ ]] || exit 0
docker compose -f docker-compose.yml exec -T mongo mongorestore --quiet --drop --archive --gzip < "$1"
docker compose -f docker-compose.yml restart backend
echo "Restored."
