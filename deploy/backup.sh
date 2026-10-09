#!/usr/bin/env bash
# Backup database + uploaded files into deploy/backups/. Usage: sudo ./deploy/backup.sh
set -euo pipefail
cd "$(dirname "$0")"
set -a; . ./.env; set +a
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p backups
docker compose -f docker-compose.yml exec -T mongo mongodump --quiet --archive --gzip --db "$DB_NAME" > "backups/db-$TS.archive.gz"
tar -czf "backups/uploads-$TS.tgz" -C data uploads
echo "Saved backups/db-$TS.archive.gz and backups/uploads-$TS.tgz"
